"""FastAPI app: upload -> read -> review -> quote -> enrol (SPEC §6).

Binds to 127.0.0.1 by default. Off localhost a shared password is required
(BILL2QUOTE_PASSWORD). LAN or Tailscale only; never port-forward.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import assess, config, enrol, extract, ingest, quote, render, store
from ..checks import WARN, has_block
from ..schema import BillFacts, Service

TEMPLATES = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))

TOP_FIELDS = ["retailer", "customer_name", "service_address", "account_number", "bill_date",
              "current_charges_total", "gst_amount", "credits_total", "confidence"]
SERVICE_FIELDS = [f for f in Service.model_fields if f != "commodity"]
FLOAT = {"current_charges_total", "gst_amount", "credits_total", "usage", "usage_m3",
         "gas_conversion_factor", "meter_previous", "meter_current", "meter_multiplier",
         "energy_rate", "energy_charge", "admin_fee", "admin_fee_rate", "delivery_total",
         "service_subtotal"}
INT = {"days"}
BOOL = {"estimated_read"}


def create_app(cfg: config.Config, data: Path = Path("data")) -> FastAPI:
    app = FastAPI(title="bill2quote")
    password = os.environ.get("BILL2QUOTE_PASSWORD", "")
    token = hmac.new(password.encode(), b"bill2quote", hashlib.sha256).hexdigest()
    status: dict[str, str] = {}

    def page(name: str, **ctx) -> HTMLResponse:
        return HTMLResponse(env.get_template(name).render(**ctx))

    @app.middleware("http")
    async def gate(request: Request, call_next):
        local = request.client and request.client.host in ("127.0.0.1", "::1", "localhost")
        if local or request.url.path == "/login":
            return await call_next(request)
        if not password:
            return HTMLResponse("Set BILL2QUOTE_PASSWORD to use bill2quote off localhost.", 403)
        if not hmac.compare_digest(request.cookies.get("b2q", ""), token):
            return RedirectResponse("/login", 303)
        return await call_next(request)

    @app.get("/login")
    def login_form():
        return page("login.html", error=False)

    @app.post("/login")
    def login(pw: str = Form("")):
        if password and hmac.compare_digest(pw, password):
            r = RedirectResponse("/", 303)
            r.set_cookie("b2q", token, httponly=True, samesite="strict")
            return r
        return page("login.html", error=True)

    @app.get("/")
    def index(ref: str = ""):
        return page("index.html", ref=ref)

    # -- upload and read -------------------------------------------------------------

    def ensure_pages(d: Path, paths: list[Path]):
        """Page images for the review screen; written once, whether or not the read is cached."""
        pages = ingest.load_pages(paths, cfg.models["max_pages"], cfg.models["max_image_side"])
        (d / "pages").mkdir(exist_ok=True)
        for i, im in enumerate(pages, 1):
            im.save(d / "pages" / f"page-{i}.png")
        return pages

    def read_in_background(sha: str, paths: list[Path]) -> None:
        d = store.bill_dir(sha, data)
        try:
            pages = ensure_pages(d, paths)
            facts, meta = extract.extract(pages, cfg.models["extract"], cfg.models["ollama_host"],
                                          cfg.models["num_ctx"], cfg.models["num_predict"])
            store.save_model_facts(d, facts, {k: v for k, v in meta.items() if k != "raw"})
            status[sha] = "done"
        except Exception as e:  # noqa: BLE001
            (d / "error.txt").write_text(str(e), encoding="utf-8")
            status[sha] = "error"

    @app.post("/upload")
    async def upload(files: list[UploadFile] = File(...), ref: str = Form("")):
        blobs = [(f.filename or "page", await f.read()) for f in files if f.filename]
        if not blobs:
            return RedirectResponse(f"/?ref={ref}", 303)
        sha = hashlib.sha256(b"".join(b for _, b in blobs)).hexdigest()[:12]
        d = store.bill_dir(sha, data)
        paths = []
        for i, (name, blob) in enumerate(blobs, 1):
            p = d / f"original-{i}{Path(name).suffix.lower()}"
            p.write_bytes(blob)
            paths.append(p)
        (d / "ref.txt").write_text(ref, encoding="utf-8")
        if store.load_facts(d) is not None:
            if not (d / "pages").exists():
                ensure_pages(d, paths)
        elif status.get(sha) != "reading":
            status[sha] = "reading"
            threading.Thread(target=read_in_background, args=(sha, paths), daemon=True).start()
        return RedirectResponse(f"/bill/{sha}/wait", 303)

    @app.get("/bill/{sha}/wait")
    def wait(sha: str):
        return page("wait.html", sha=sha)

    @app.get("/bill/{sha}/status")
    def state(sha: str):
        d = data / "bills" / sha
        if store.load_facts(d):
            return {"state": "done"}
        if (d / "error.txt").exists() and status.get(sha) != "reading":
            return {"state": "error", "message": (d / "error.txt").read_text(encoding="utf-8")}
        return {"state": "reading"}

    @app.get("/bill/{sha}/page/{n}.png")
    def page_image(sha: str, n: int):
        p = data / "bills" / sha / "pages" / f"page-{n}.png"
        return FileResponse(p) if p.exists() else Response(status_code=404)

    # -- review ----------------------------------------------------------------------

    def load(sha: str):
        d = data / "bills" / sha
        got = store.load_facts(d)
        if got is None:
            return d, None, None
        return d, got[0], json.loads((d / "facts.model.json").read_text(encoding="utf-8"))["facts"]

    def quote_inputs(params) -> tuple[dict, dict, str]:
        """Offer choices and annual-usage overrides from a query string or form, plus the
        query string that carries them between the review and quote pages."""
        got = {k: (params.get(k) or "").strip() for k in ("elec", "gas", "annual_elec", "annual_gas")}
        offer_ids = {c: got[k] for c, k in (("electricity", "elec"), ("gas", "gas")) if got[k]}
        override = {}
        for c, k in (("electricity", "annual_elec"), ("gas", "annual_gas")):
            if got[k]:
                try:
                    override[c] = Decimal(got[k].replace(",", ""))
                except InvalidOperation:
                    pass
        qs = urlencode({k: v for k, v in got.items() if v})
        return offer_ids, override, qs

    def flags_for(facts: BillFacts, sha: str, params=None):
        """Bill checks, the quote plausibility check (C19), and any reviewer override."""
        offer_ids, override, _ = quote_inputs(params or {})
        return assess.assess(facts, cfg, data / "bills" / sha,
                             store.seen_sites(data, exclude=sha), offer_ids, override)

    def log_event(event: dict) -> None:
        with (data / "log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")

    def try_override(form, sha: str, facts: BillFacts, flags, params) -> tuple[list, str, bool]:
        """Apply the reviewer's override if they asked for it. Returns (flags, problem, applied)."""
        if form.get("override") != "on":
            return flags, "", False
        reason = (form.get("override_reason") or "").strip()
        if not assess.can_override(flags):
            return flags, "These blocks can't be overridden. Fix the red fields.", False
        if not reason:
            return flags, "Say why the numbers are right to override. The reason is saved.", False
        entry = assess.save_override(data / "bills" / sha, reason, assess.overridable_blocks(flags))
        log_event({"at": entry["at"], "bill": sha, "override": entry})
        return flags_for(facts, sha, params), "", True

    def render_review(request: Request, sha: str, facts: BillFacts, errors: list[str]):
        d = data / "bills" / sha
        flags = flags_for(facts, sha, request.query_params)
        by_field: dict[str, list] = {}
        for f in flags:
            by_field.setdefault(f.field, []).append(f)
        n_pages = len(list((d / "pages").glob("page-*.png")))
        return page("review.html", sha=sha, facts=facts, flags=flags, by_field=by_field,
                    top_fields=TOP_FIELDS, service_fields=SERVICE_FIELDS, errors=errors,
                    values=facts.model_dump(), svc_values=[s.model_dump() for s in facts.services],
                    n_pages=n_pages, needs_ack=any(f.severity == WARN for f in flags),
                    overridable=assess.overridable_blocks(flags) if assess.can_override(flags) else [],
                    ref=(d / "ref.txt").read_text(encoding="utf-8") if (d / "ref.txt").exists() else "")

    @app.get("/bill/{sha}/review")
    def review(request: Request, sha: str):
        _, facts, _ = load(sha)
        if facts is None:
            return RedirectResponse(f"/bill/{sha}/wait", 303)
        return render_review(request, sha, facts, [])

    def convert(name: str, raw: str):
        raw = (raw or "").strip()
        if raw == "":
            return None
        if name in BOOL:
            return raw == "true"
        if name in INT:
            return int(float(raw))
        if name in FLOAT:
            return float(raw.replace(",", "").replace("$", ""))
        return raw

    @app.post("/bill/{sha}/review")
    async def review_post(request: Request, sha: str):
        d, current, model = load(sha)
        if current is None:
            return RedirectResponse(f"/bill/{sha}/wait", 303)
        form = await request.form()
        new = json.loads(current.model_dump_json())
        errors: list[str] = []
        try:
            for f in TOP_FIELDS:
                new[f] = convert(f, form.get(f"top.{f}", ""))
            for i, s in enumerate(new["services"]):
                for f in SERVICE_FIELDS:
                    s[f] = convert(f, form.get(f"s{i}.{f}", ""))
            new["unreadable"] = new.get("unreadable", [])
            facts = BillFacts.model_validate(new)
        except (ValueError, InvalidOperation) as e:
            return render_review(request, sha, current, [f"Could not read your edits: {e}"])

        # edit log: every difference from what the model said (SPEC §5.3)
        now = datetime.now(UTC).isoformat(timespec="seconds")
        edits = []
        m, n = model, json.loads(facts.model_dump_json())
        for f in TOP_FIELDS:
            if m[f] != n[f]:
                edits.append(dict(field=f, model_value=m[f], new_value=n[f], at=now))
        for i, s in enumerate(n["services"]):
            for f in SERVICE_FIELDS:
                if m["services"][i][f] != s[f]:
                    edits.append(dict(field=f"services[{i}].{f}", model_value=m["services"][i][f],
                                      new_value=s[f], at=now))
        flags = flags_for(facts, sha, request.query_params)
        overrode = False
        if has_block(flags):
            flags, problem, overrode = try_override(form, sha, facts, flags, request.query_params)
            if has_block(flags):
                return render_review(request, sha, facts,
                                     [problem or "Fix the red fields before confirming."])
        acked = form.get("ack") == "on" or overrode  # overriding means the reviewer looked
        if any(f.severity == WARN for f in flags) and not acked:
            return render_review(request, sha, facts, ["Tick “I checked the flagged fields”."])
        store.save_reviewed(d, facts, edits)
        (d / "flags.json").write_text(json.dumps([f.to_dict() for f in flags], indent=2),
                                      encoding="utf-8")
        (d / "acked.txt").write_text(str(acked), encoding="utf-8")
        with (data / "log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": now, "bill": sha, "edits": edits}) + "\n")
        _, _, qs = quote_inputs(request.query_params)
        view = request.query_params.get("view", "")
        qs = "&".join(x for x in (qs, f"view={view}" if view in ("customer", "staff") else "") if x)
        return RedirectResponse(f"/bill/{sha}/quote" + (f"?{qs}" if qs else ""), 303)

    # -- quote and enrol -------------------------------------------------------------

    def reviewed(sha: str):
        d = data / "bills" / sha
        p = d / "facts.reviewed.json"
        if not p.exists():
            return None
        j = json.loads(p.read_text(encoding="utf-8"))
        return BillFacts.model_validate(j["facts"]), j.get("edits", [])

    @app.get("/bill/{sha}/quote")
    def quote_page(request: Request, sha: str, view: str = "customer", elec: str = "",
                   gas: str = "", annual_elec: str = "", annual_gas: str = ""):
        got = reviewed(sha)
        if got is None:
            return RedirectResponse(f"/bill/{sha}/review", 303)
        facts, edits = got
        params = {"elec": elec, "gas": gas, "annual_elec": annual_elec, "annual_gas": annual_gas}
        flags = flags_for(facts, sha, params)
        offer_ids, override, back_qs = quote_inputs(params)
        if has_block(flags):  # never show a comparison that failed a blocking check
            return page("quote_blocked.html", sha=sha, qs=back_qs, offers_chosen=bool(offer_ids),
                        flags=[f for f in flags if assess.is_blocking(f)],
                        can_override=assess.can_override(flags))
        q = quote.build_quote(facts, cfg, offer_ids, override)
        d = data / "bills" / sha
        ref = (d / "ref.txt").read_text(encoding="utf-8") if (d / "ref.txt").exists() else ""
        qs = "".join(f"&{k}={v}" for k, v in (("elec", elec), ("gas", gas),
                     ("annual_elec", annual_elec), ("annual_gas", annual_gas)) if v)
        html = render.render_quote(facts, q, flags, cfg, view=view if view in ("customer", "staff")
                                   else "customer", partner=ref, edits=edits, query=qs)
        bar = env.get_template("quote_bar.html").render(
            sha=sha, back_qs=urlencode({k: v for k, v in {**params, "view": view}.items() if v}), offers=cfg.offers, elec=elec, gas=gas, annual_elec=annual_elec,
            annual_gas=annual_gas, view=view, blocked_enrol=has_block(flags, True))
        (d / f"quote-{view}.html").write_text(html, encoding="utf-8")
        return HTMLResponse(html.replace("<main>", "<main>" + bar, 1))

    @app.post("/bill/{sha}/override")
    async def override_post(request: Request, sha: str):
        """Override from the blocked-quote page: same rules as on the review form."""
        got = reviewed(sha)
        if got is None:
            return RedirectResponse(f"/bill/{sha}/review", 303)
        facts, _ = got
        form = await request.form()
        qs = str(form.get("qs") or "")
        params = dict(parse_qsl(qs))
        flags = flags_for(facts, sha, params)
        if has_block(flags):
            _, problem, _ = try_override({"override": "on", **form}, sha, facts, flags, params)
            if problem:
                return HTMLResponse(problem, 400)
        return RedirectResponse(f"/bill/{sha}/quote" + (f"?{qs}" if qs else ""), 303)

    @app.post("/bill/{sha}/enrol")
    def enrol_post(sha: str, elec: str = Form(""), gas: str = Form("")):
        got = reviewed(sha)
        if got is None:
            return RedirectResponse(f"/bill/{sha}/review", 303)
        facts, _ = got
        flags = flags_for(facts, sha, {"elec": elec, "gas": gas})
        if has_block(flags, for_enrolment=True):
            return HTMLResponse("Blocking flag: fix site IDs on the review screen first.", 400)
        d = data / "bills" / sha
        ref = (d / "ref.txt").read_text(encoding="utf-8") if (d / "ref.txt").exists() else ""
        ids = {c: v for c, v in (("electricity", elec), ("gas", gas)) if v}
        acked = (d / "acked.txt").exists() and (d / "acked.txt").read_text() == "True"
        enrol.append(data / "enrolments.csv", enrol.rows_for(facts, ref, sha, ids, acked))
        return RedirectResponse("/enrolments", 303)

    @app.get("/enrolments")
    def enrolments():
        p = data / "enrolments.csv"
        rows = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
        return page("enrolments.html", rows=[r for r in rows[1:]], count=max(len(rows) - 1, 0))

    @app.get("/enrolments.csv")
    def enrolments_csv():
        p = data / "enrolments.csv"
        if not p.exists():
            return JSONResponse({"error": "no enrolments yet"}, 404)
        return FileResponse(p, media_type="text/csv", filename="enrolments.csv")

    return app
