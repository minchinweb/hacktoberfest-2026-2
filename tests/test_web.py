import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bill2quote import config, store
from bill2quote.schema import BillFacts
from bill2quote.web.app import SERVICE_FIELDS, TOP_FIELDS, create_app

CFG = config.load("config.example.toml")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BILL2QUOTE_PASSWORD", "pw")
    c = TestClient(create_app(CFG, tmp_path), follow_redirects=False)
    c.tmp = tmp_path
    return c


def seed(client, name="07_inconsistent", sha="abc123abc123"):
    truth = BillFacts.model_validate(
        json.loads(Path(f"samples/{name}.truth.json").read_text(encoding="utf-8")))
    d = store.bill_dir(sha, client.tmp)
    store.save_model_facts(d, truth, {"model": "test"})
    (d / "pages").mkdir(exist_ok=True)
    return sha, truth


def form_for(facts: BillFacts, **over):
    f = {}
    for k in TOP_FIELDS:
        v = getattr(facts, k)
        f[f"top.{k}"] = "" if v is None else str(v)
    for i, s in enumerate(facts.services):
        for k in SERVICE_FIELDS:
            v = getattr(s, k)
            f[f"s{i}.{k}"] = "" if v is None else str(v).lower() if isinstance(v, bool) else str(v)
    f.update(over)
    return f


def login(client):
    assert client.post("/login", data={"pw": "pw"}).status_code == 303


def test_password_required_off_localhost(client):
    assert client.get("/").status_code == 303  # redirect to /login
    assert client.post("/login", data={"pw": "wrong"}).status_code == 200
    login(client)
    assert client.get("/").status_code == 200


def test_planted_error_needs_ack_and_a_fix_is_logged(client):
    login(client)
    sha, truth = seed(client)
    assert "C01" in client.get(f"/bill/{sha}/review").text  # shown beside the field
    printed = truth.services[0].energy_charge
    # Unchanged and not acknowledged: refused, nothing saved.
    r = client.post(f"/bill/{sha}/review", data=form_for(truth))
    assert r.status_code == 200 and "I checked the flagged fields" in r.text
    assert not (client.tmp / "bills" / sha / "facts.reviewed.json").exists()
    # Reviewer corrects the charge to usage x rate; the edit is recorded.
    fixed = form_for(truth, **{"s0.energy_charge": str(printed - 20)})
    assert client.post(f"/bill/{sha}/review", data=fixed).status_code == 303  # C01 cleared
    j = json.loads((client.tmp / "bills" / sha / "facts.reviewed.json").read_text())
    edit = next(e for e in j["edits"] if e["field"] == "services[0].energy_charge")
    assert edit["model_value"] == printed and edit["new_value"] == printed - 20


def test_customer_view_masks_site_and_hides_flags_staff_shows_both(client):
    login(client)
    sha, truth = seed(client, "01_elec_clean")
    r = client.post(f"/bill/{sha}/review", data=form_for(truth))
    assert r.status_code == 303
    cust = client.get(f"/bill/{sha}/quote?view=customer").text
    assert "0010099000011" not in cust and "0011" in cust
    assert "Flags (staff only)" not in cust
    staff = client.get(f"/bill/{sha}/quote?view=staff").text
    assert "0010099000011" in staff and "Flags (staff only)" in staff


def test_negative_savings_page_renders_plainly(client):
    login(client)
    sha, truth = seed(client, "08_already_cheaper")
    client.post(f"/bill/{sha}/review", data=form_for(truth))
    html = client.get(f"/bill/{sha}/quote").text
    assert "your current plan is cheaper" in html


def test_enrolment_csv_omits_account_number(client):
    login(client)
    sha, truth = seed(client, "03_dual_fuel_2page")
    client.post(f"/bill/{sha}/review", data=form_for(truth))
    assert client.post(f"/bill/{sha}/enrol", data={"elec": "elec-fixed-3y",
                                                   "gas": "gas-fixed-3y"}).status_code == 303
    csv_text = (client.tmp / "enrolments.csv").read_text(encoding="utf-8")
    assert "0010099000013" in csv_text and "0000099000014" in csv_text
    assert truth.account_number not in csv_text
    assert len(csv_text.strip().splitlines()) == 3  # header + two sites


def test_bad_site_id_blocks_enrolment_not_quote(client):
    login(client)
    sha, truth = seed(client, "01_elec_clean")
    data = form_for(truth, **{"s0.site_id": "12345"})
    assert client.post(f"/bill/{sha}/review", data=data).status_code == 303
    assert client.get(f"/bill/{sha}/quote").status_code == 200
    assert client.post(f"/bill/{sha}/enrol", data={}).status_code == 400


def test_upload_of_an_already_read_bill_still_gets_page_images(client):
    import hashlib
    login(client)
    blob = Path("samples/01_elec_clean.pdf").read_bytes()
    sha = hashlib.sha256(blob).hexdigest()[:12]
    seed(client, "01_elec_clean", sha=sha)
    (client.tmp / "bills" / sha / "pages").rmdir()
    r = client.post("/upload", files=[("files", ("b.pdf", blob, "application/pdf"))])
    assert r.status_code == 303
    assert client.get(f"/bill/{sha}/page/1.png").status_code == 200


def test_misread_usage_is_refused_then_fixed_and_the_comparison_reruns(client):
    login(client)
    sha, truth = seed(client, "02_gas_clean")
    # The m3 figure in the GJ field; every other field right. Charge no longer matches usage x rate.
    bad = form_for(truth, **{"s0.usage": "981.4"})
    r = client.post(f"/bill/{sha}/review", data=bad)
    assert r.status_code == 200 and "Fix the red fields" in r.text and "C01" in r.text
    assert not (client.tmp / "bills" / sha / "facts.reviewed.json").exists()
    # Back on the form with the correct usage, the comparison runs.
    r = client.post(f"/bill/{sha}/review", data=form_for(truth), follow_redirects=False)
    assert r.status_code == 303
    assert "You would have saved" in client.get(f"/bill/{sha}/quote").text


def test_quote_page_never_shows_an_implausible_comparison(client):
    login(client)
    sha, truth = seed(client, "02_gas_clean")
    s = truth.services[0]
    s.usage, s.energy_rate, s.energy_rate_unit = 981.4, None, None  # no printed rate: C01 can't fire
    store.save_reviewed(store.bill_dir(sha, client.tmp), truth, [])
    html = client.get(f"/bill/{sha}/quote?view=customer&gas=gas-fixed-3y").text
    assert "can't be shown yet" in html and "C19" in html
    assert "You would have saved" not in html and "cheaper by" not in html
    assert "/bill/" + sha + "/review?gas=gas-fixed-3y" in html  # the way back keeps the offer choice


def test_edit_numbers_and_rerun_keeps_offer_choices(client):
    login(client)
    sha, truth = seed(client, "01_elec_clean")
    client.post(f"/bill/{sha}/review", data=form_for(truth))
    html = client.get(f"/bill/{sha}/quote?elec=elec-fixed-3y&annual_elec=7000").text
    assert "Edit numbers and re-run" in html
    form = client.get(f"/bill/{sha}/review?elec=elec-fixed-3y&annual_elec=7000")
    assert form.status_code == 200 and "70.32" in form.text  # shows the saved numbers
    r = client.post(f"/bill/{sha}/review?elec=elec-fixed-3y&annual_elec=7000",
                    data=form_for(truth, **{"s0.admin_fee": "9.0"}))
    assert r.status_code == 303
    assert "elec=elec-fixed-3y" in r.headers["location"] and "annual_elec=7000" in r.headers["location"]
