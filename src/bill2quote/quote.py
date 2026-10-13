"""Quote math (SPEC §10). Decimal throughout; rounding happens only at display.

Positive `diff` means the customer saves. Only the energy charge and the admin fee are the
retailer's; delivery, riders and local fees are the same whichever retailer is chosen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .annualize import annual_usage
from .checks import rate_per_unit
from .config import Config, Offer
from .schema import BillFacts, Service

CENT = Decimal("0.01")


def cents(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class ServiceQuote:
    commodity: str
    site_id: str | None
    offer: Offer
    usage: Decimal
    unit: str
    days: int
    current_energy: Decimal
    current_admin: Decimal
    current_rate_eff: Decimal
    offer_energy: Decimal
    offer_admin: Decimal
    diff_pre_gst: Decimal
    diff: Decimal  # incl. GST; positive = customer saves
    annual_usage: Decimal
    annual_method: str
    annual_diff: Decimal


@dataclass
class Quote:
    services: list[ServiceQuote] = field(default_factory=list)
    credits_excluded: Decimal = Decimal(0)

    @property
    def total_diff(self) -> Decimal:
        return sum((s.diff for s in self.services), Decimal(0))

    @property
    def total_annual_diff(self) -> Decimal:
        return sum((s.annual_diff for s in self.services), Decimal(0))


def quote_service(s: Service, offer: Offer, cfg: Config,
                  annual_override: Decimal | None = None) -> ServiceQuote:
    u = Decimal(str(s.usage))
    days = int(s.days)
    if s.energy_charge is not None:
        energy = Decimal(str(s.energy_charge))
    else:
        energy = u * rate_per_unit(s)
    if s.admin_fee is not None:
        admin = Decimal(str(s.admin_fee))
    else:
        admin = Decimal(str(s.admin_fee_rate)) * days
    gst = 1 + cfg.gst_rate

    rate_eff = energy / u
    offer_energy = u * offer.energy_rate
    offer_admin = offer.admin_fee_per_day * days
    diff_pre = (energy + admin) - (offer_energy + offer_admin)

    annual_u, method = annual_usage(s, cfg, annual_override)
    annual_diff = ((rate_eff - offer.energy_rate) * annual_u
                   + (admin / days - offer.admin_fee_per_day) * 365) * gst
    return ServiceQuote(
        commodity=s.commodity, site_id=s.site_id, offer=offer, usage=u, unit=s.usage_unit or "",
        days=days, current_energy=energy, current_admin=admin, current_rate_eff=rate_eff,
        offer_energy=offer_energy, offer_admin=offer_admin, diff_pre_gst=diff_pre,
        diff=diff_pre * gst, annual_usage=annual_u, annual_method=method, annual_diff=annual_diff)


def build_quote(facts: BillFacts, cfg: Config, offer_ids: dict[str, str] | None = None,
                annual_override: dict[str, Decimal] | None = None) -> Quote:
    """One offer per commodity. `offer_ids` maps commodity -> offer id; default is the first
    configured offer for that commodity."""
    q = Quote(credits_excluded=Decimal(str(facts.credits_total or 0)))
    for s in facts.services:
        oid = (offer_ids or {}).get(s.commodity)
        offer = cfg.offer(oid) if oid else next(
            (o for o in cfg.offers if o.commodity == s.commodity), None)
        if offer is None:
            continue
        q.services.append(quote_service(s, offer, cfg, (annual_override or {}).get(s.commodity)))
    return q
