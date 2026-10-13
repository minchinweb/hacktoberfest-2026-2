"""Annual usage estimate (SPEC §10). The method used is always returned with the number."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from .config import Config
from .schema import Service


def hdd_share(start: date, days: int, hdd_monthly: list, base: Decimal) -> Decimal:
    """Expected share of annual gas use falling in [start, start+days)."""
    hdd = [Decimal(str(h)) for h in hdd_monthly]
    total = sum(hdd)
    share = Decimal(0)
    for i in range(days):
        d = start + timedelta(days=i)
        dim = calendar.monthrange(d.year, d.month)[1]
        share += base / 365 + (1 - base) * (hdd[d.month - 1] / dim) / total
    return share


def annual_usage(s: Service, cfg: Config, override: Decimal | None = None) -> tuple[Decimal, str]:
    """(annual usage in kWh or GJ, plain-words method). Needs s.usage and s.days."""
    u, days = Decimal(str(s.usage)), int(s.days)
    if override is not None:
        return override, "Annual usage entered by the reviewer."
    if s.commodity == "gas":
        hdd = cfg.raw["annualize"]["hdd_monthly"]
        base = Decimal(cfg.raw["annualize"]["gas_base_fraction"])
        if len(hdd) == 12 and s.period_start:
            share = hdd_share(date.fromisoformat(s.period_start), days, hdd, base)
            return u / share, (
                f"Scaled from this bill using Edmonton heating-degree-day normals; "
                f"assumes {base * 100:.0f}% of annual gas use is not weather-related.")
        return u * 365 / days, (
            "ROUGH: scaled from this bill's daily usage with no weather adjustment. Gas use "
            "swings with the seasons, so a summer bill understates and a winter bill overstates "
            "the year. Enter the customer's annual usage if known.")
    return u * 365 / days, "Assumes this bill is a typical month."
