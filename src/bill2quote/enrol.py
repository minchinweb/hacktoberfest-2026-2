"""Enrolment CSV (SPEC §8.3). The old account number is never exported."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from .schema import BillFacts

COLUMNS = ["created_at", "ref", "bill_sha", "customer_name", "service_address", "commodity",
           "site_id", "current_retailer", "offer_id", "flags_checked"]


def rows_for(facts: BillFacts, ref: str, bill_sha: str, offer_ids: dict[str, str],
             flags_checked: bool) -> list[dict]:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    return [dict(created_at=now, ref=ref, bill_sha=bill_sha, customer_name=facts.customer_name,
                 service_address=facts.service_address, commodity=s.commodity,
                 site_id=(s.site_id or "").replace(" ", ""), current_retailer=facts.retailer,
                 offer_id=offer_ids.get(s.commodity, ""), flags_checked=str(flags_checked).lower())
            for s in facts.services]


def append(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerows(rows)
