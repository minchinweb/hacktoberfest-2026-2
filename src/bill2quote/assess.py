"""All the flags for a bill, with reviewer overrides applied (SPEC §9, §5.3).

The bill checks run first. Once none of them is a hard block, the quote plausibility check (C19)
runs on top, using the offers in play. A blocking flag marked `overridable` (a likely misread, such
as C01 far apart or C19) can be overridden by a reviewer who gives a reason. The override is stored
against the exact flag text, so editing a number, or choosing another offer, changes the flag and
the override no longer applies: the reviewer has to look again.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from . import quote
from .checks import BLOCK, WARN, Flag, check_bill, has_block
from .config import Config
from .schema import BillFacts

FILE = "override.json"


def fingerprint(f: Flag) -> str:
    return f"{f.id}|{f.field}|{f.message}"


def load_overrides(d: Path | None) -> list[dict]:
    p = d / FILE if d else None
    return json.loads(p.read_text(encoding="utf-8"))["entries"] if p and p.exists() else []


def save_override(d: Path, reason: str, flags: list[Flag]) -> dict:
    entry = dict(at=datetime.now(UTC).isoformat(timespec="seconds"), reason=reason.strip(),
                 flags=[fingerprint(f) for f in flags])
    (d / FILE).write_text(json.dumps({"entries": load_overrides(d) + [entry]}, indent=2),
                          encoding="utf-8")
    return entry


def apply_overrides(flags: list[Flag], entries: list[dict]) -> list[Flag]:
    """Overridden blocking flags become warnings that carry the reviewer's reason."""
    out = []
    for f in flags:
        entry = next((e for e in entries if fingerprint(f) in e["flags"]), None)
        if f.severity == BLOCK and f.overridable and entry:
            f = replace(f, severity=WARN, overridden=True,
                        message=f"Overridden by reviewer ({entry['reason']}). {f.message}")
        out.append(f)
    return out


def is_blocking(f: Flag) -> bool:
    """Blocks the quote (a block that only stops enrolment does not)."""
    return f.severity == BLOCK and not f.enrol_only


def overridable_blocks(flags: list[Flag]) -> list[Flag]:
    return [f for f in flags if is_blocking(f) and f.overridable]


def can_override(flags: list[Flag]) -> bool:
    """There is something to override, and nothing that cannot be overridden."""
    return bool(overridable_blocks(flags)) and all(f.overridable for f in flags if is_blocking(f))


def assess(facts: BillFacts, cfg: Config, d: Path | None = None,
           seen: set[tuple[str, str]] | None = None, offer_ids: dict[str, str] | None = None,
           annual_override: dict[str, Decimal] | None = None) -> list[Flag]:
    entries = load_overrides(d)
    flags = apply_overrides(check_bill(facts, cfg, seen), entries)
    if not any(is_blocking(f) and not f.overridable for f in flags):
        try:
            flags += quote.quote_flags(quote.build_quote(facts, cfg, offer_ids, annual_override), cfg)
        except (ArithmeticError, TypeError, ValueError):
            pass  # a figure the quote cannot use is already flagged by the bill checks
        flags = apply_overrides(flags, entries)
    return flags


__all__ = ["assess", "can_override", "has_block", "overridable_blocks", "save_override"]
