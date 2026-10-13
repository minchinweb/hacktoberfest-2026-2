import json
from pathlib import Path

from bill2quote import cli, store
from bill2quote.schema import BillFacts

CFG = str(Path("config.example.toml").resolve())
TRUTH = Path("samples/01_elec_clean.truth.json").read_text(encoding="utf-8")


def seed_bill(inbox: Path, name: str, content: bytes, truth: str = TRUTH) -> None:
    """A file in the inbox plus a cached read, so no model is needed."""
    (inbox / name).write_bytes(content)
    d = store.bill_dir(store.sha12([inbox / name]))
    store.save_model_facts(d, BillFacts.model_validate(json.loads(truth)), {"model": "test"})


def run_batch(capsys, inbox: Path) -> dict[str, str]:
    assert cli.main(["--config", CFG, "batch", str(inbox)]) == 0
    lines = capsys.readouterr().out.splitlines()[1:]
    return {line.split()[0]: line for line in lines}


def test_batch_flags_the_same_site_and_period_seen_twice(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    seed_bill(inbox, "a.pdf", b"first scan")
    seed_bill(inbox, "b.pdf", b"second scan of the same bill")
    out = run_batch(capsys, inbox)
    assert "C16" in out["a.pdf"] and "C16" in out["b.pdf"]


def test_batch_does_not_flag_a_bill_against_itself(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    seed_bill(inbox, "only.pdf", b"just one")
    assert "C16" not in run_batch(capsys, inbox)["only.pdf"]
