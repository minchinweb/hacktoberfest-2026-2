"""SHA-addressed bill folders under data/ (SPEC §7). Re-uploading the same file is a no-op."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .schema import BillFacts

DATA = Path("data")


def sha12(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def bill_dir(sha: str, root: Path = DATA) -> Path:
    d = root / "bills" / sha
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_model_facts(d: Path, facts: BillFacts, meta: dict) -> None:
    (d / "facts.model.json").write_text(
        json.dumps({"facts": facts.model_dump(), "meta": meta}, indent=2), encoding="utf-8")


def load_facts(d: Path) -> tuple[BillFacts, dict] | None:
    """Reviewed facts if present, else the model's. None if the bill was never read."""
    for name in ("facts.reviewed.json", "facts.model.json"):
        p = d / name
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return BillFacts.model_validate(data["facts"]), data
    return None


def save_reviewed(d: Path, facts: BillFacts, edits: list[dict]) -> None:
    (d / "facts.reviewed.json").write_text(
        json.dumps({"facts": facts.model_dump(), "edits": edits,
                    "reviewed_at": datetime.now(UTC).isoformat(timespec="seconds")},
                   indent=2), encoding="utf-8")


def seen_sites(root: Path = DATA, exclude: str = "") -> set[tuple[str, str]]:
    """(site_id, period_end) pairs in other bills, for flag C16."""
    out: set[tuple[str, str]] = set()
    for p in (root / "bills").glob("*/facts.*.json"):
        if p.parent.name == exclude:
            continue
        facts = BillFacts.model_validate(json.loads(p.read_text(encoding="utf-8"))["facts"])
        out |= {(s.site_id, s.period_end) for s in facts.services if s.site_id and s.period_end}
    return out
