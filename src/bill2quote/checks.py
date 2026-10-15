"""Deterministic checks on BillFacts (SPEC §9). Pure functions, no model needed."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from .config import Config
from .schema import BillFacts, Service

BLOCK, WARN, INFO = "BLOCK", "WARN", "INFO"
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Flag:
    id: str
    severity: str
    field: str
    message: str
    # BLOCK for enrolment only: the quote can still be made, the enrolment row cannot.
    enrol_only: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def D(x) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def close(a: Decimal, b: Decimal, cfg: Config) -> bool:
    """Within max(money tolerance, pct tolerance of the larger value)."""
    tol = max(cfg.money_tol, cfg.pct_tol * max(abs(a), abs(b)))
    return abs(a - b) <= tol


def _where(i: int, name: str) -> str:
    return f"services[{i}].{name}"


def _days_between(start: str | None, end: str | None) -> int | None:
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def rate_per_unit(s: Service) -> Decimal | None:
    """Energy rate normalised to $/kWh or $/GJ. None if the unit is unknown."""
    r = D(s.energy_rate)
    if r is None:
        return None
    if s.energy_rate_unit == "cents_per_kWh":
        return r / 100
    if s.energy_rate_unit in ("dollars_per_kWh", "dollars_per_GJ"):
        return r
    return None


def check_service(i: int, s: Service, facts: BillFacts, cfg: Config) -> list[Flag]:
    f: list[Flag] = []
    c = cfg.checks
    lab = s.commodity

    # C12 missing quote-critical values
    if s.usage is None:
        f.append(Flag("C12", BLOCK, _where(i, "usage"), f"{lab}: usage is missing."))
    elif D(s.usage) <= 0:
        f.append(Flag("C12", BLOCK, _where(i, "usage"), f"{lab}: usage must be more than zero."))
    if s.days is None:
        f.append(Flag("C12", BLOCK, _where(i, "days"), f"{lab}: days is missing."))
    elif s.days <= 0:
        f.append(Flag("C12", BLOCK, _where(i, "days"), f"{lab}: days must be more than zero."))
    if s.energy_charge is None and s.energy_rate is None:
        f.append(Flag("C12", BLOCK, _where(i, "energy_charge"),
                      f"{lab}: energy charge and rate are both missing."))
    if s.admin_fee is None and s.admin_fee_rate is None:
        f.append(Flag("C12", BLOCK, _where(i, "admin_fee"), f"{lab}: admin fee is missing."))

    # C14 unknown rate unit / C06 plausible range
    if s.energy_rate is not None:
        if s.energy_rate_unit is None:
            f.append(Flag("C14", BLOCK, _where(i, "energy_rate_unit"),
                          f"{lab}: rate unit is unknown."))
        else:
            r = D(s.energy_rate)
            if s.energy_rate_unit == "cents_per_kWh":
                lo, hi = (D(x) for x in c["elec_rate_cents_range"])
                unit_txt = "¢/kWh"
            elif s.energy_rate_unit == "dollars_per_kWh":
                lo, hi = (D(x) / 100 for x in c["elec_rate_cents_range"])
                unit_txt = "$/kWh"
            else:
                lo, hi = (D(x) for x in c["gas_rate_dollars_range"])
                unit_txt = "$/GJ"
            if not lo <= r <= hi:
                f.append(Flag("C06", BLOCK, _where(i, "energy_rate"),
                              f"{lab}: rate {r} {unit_txt} is outside {lo}–{hi}. "
                              "Check for a ¢ vs $ mix-up."))

    # C01 charge ≈ usage × rate
    rate = rate_per_unit(s)
    u, ch = D(s.usage), D(s.energy_charge)
    if u is not None and rate is not None and ch is not None and not close(ch, u * rate, cfg):
        exp = u * rate
        shown = (f"{lab}: charge {ch} ≠ usage {u} × rate {rate} = {exp.quantize(CENT)}.")
        if exp > 0 and ch > 0 and not (1 / cfg.implausible_ratio <= ch / exp <= cfg.implausible_ratio):
            # No tiered or blended rate explains a gap this big: a number was misread.
            f.append(Flag("C01", BLOCK, _where(i, "energy_charge"),
                          f"{shown} They are more than {cfg.implausible_ratio}× apart, so usage, "
                          "rate or charge was misread."))
        else:
            f.append(Flag("C01", WARN, _where(i, "energy_charge"),
                          f"{shown} May be a tiered or blended rate."))

    # C02 days vs period dates (inclusive or exclusive counting)
    span = _days_between(s.period_start, s.period_end)
    if span is not None and s.days is not None and s.days not in (span, span + 1):
        f.append(Flag("C02", WARN, _where(i, "days"),
                      f"{lab}: days {s.days} does not match period dates ({span} days apart)."))

    # C03 admin fee ≈ rate × days
    if (s.admin_fee_basis == "per_day" and s.admin_fee_rate is not None
            and s.days is not None and s.admin_fee is not None):
        exp = D(s.admin_fee_rate) * s.days
        if not close(D(s.admin_fee), exp, cfg):
            f.append(Flag("C03", WARN, _where(i, "admin_fee"),
                          f"{lab}: admin fee {s.admin_fee} ≠ {s.admin_fee_rate} × {s.days} days "
                          f"= {exp.quantize(CENT)}."))

    # C04 electricity meter arithmetic
    if s.commodity == "electricity" and None not in (s.meter_previous, s.meter_current, s.usage):
        mult = D(s.meter_multiplier) if s.meter_multiplier is not None else Decimal(1)
        exp = (D(s.meter_current) - D(s.meter_previous)) * mult
        if not close(exp, D(s.usage), cfg):
            f.append(Flag("C04", WARN, _where(i, "usage"),
                          f"{lab}: meter reads give {exp} kWh but usage says {s.usage}."))

    # C05 gas m³ × factor ≈ GJ, factor in range
    if s.commodity == "gas":
        if s.gas_conversion_factor is not None:
            lo, hi = (D(x) for x in c["gas_factor_range"])
            if not lo <= D(s.gas_conversion_factor) <= hi:
                f.append(Flag("C05", WARN, _where(i, "gas_conversion_factor"),
                              f"{lab}: conversion factor {s.gas_conversion_factor} is outside "
                              f"{lo}–{hi} GJ/m³."))
        if None not in (s.usage_m3, s.gas_conversion_factor, s.usage):
            exp = D(s.usage_m3) * D(s.gas_conversion_factor)
            if not close(exp, D(s.usage), cfg):
                f.append(Flag("C05", WARN, _where(i, "usage"),
                              f"{lab}: {s.usage_m3} m³ × {s.gas_conversion_factor} = "
                              f"{exp.quantize(Decimal('0.001'))} GJ but usage says {s.usage}."))

    # C07 site id format (BLOCK for enrolment only)
    rx = c["site_id_regex"][s.commodity]
    if s.site_id is None or not re.match(rx, s.site_id.replace(" ", "")):
        f.append(Flag("C07", BLOCK, _where(i, "site_id"),
                      f"{lab}: site ID {s.site_id!r} is not 13 digits starting with "
                      f"{'000' if s.commodity == 'gas' else '00'}.",
                      enrol_only=True))

    # C17 site id equals account number
    if (s.site_id and facts.account_number
            and s.site_id.replace(" ", "") == facts.account_number.replace(" ", "")):
        f.append(Flag("C17", BLOCK, _where(i, "site_id"),
                      f"{lab}: site ID equals the account number; likely the wrong field.",
                      enrol_only=True))

    # C10 period length
    n = s.days if s.days is not None else span
    if n is not None:
        lo, hi = c["period_days_range"]
        if not lo <= n <= hi:
            f.append(Flag("C10", INFO, _where(i, "days"),
                          f"{lab}: billing period is {n} days (usual {lo}–{hi})."))

    # C15 estimated read
    if s.estimated_read:
        f.append(Flag("C15", INFO, _where(i, "estimated_read"),
                      f"{lab}: meter read was estimated; usage may be adjusted later."))
    return f


def check_bill(facts: BillFacts, cfg: Config,
               seen: set[tuple[str, str]] | None = None) -> list[Flag]:
    """Run every check. `seen` holds (site_id, period_end) pairs already processed (C16)."""
    flags: list[Flag] = []
    for i, s in enumerate(facts.services):
        flags += check_service(i, s, facts, cfg)
        if seen is not None and s.site_id and s.period_end and (s.site_id, s.period_end) in seen:
            flags.append(Flag("C16", INFO, _where(i, "site_id"),
                              f"{s.commodity}: this site and period were already processed."))

    # C08 sum of subtotals + GST - credits ≈ current charges
    subs = [D(s.service_subtotal) for s in facts.services]
    total, gst = D(facts.current_charges_total), D(facts.gst_amount)
    credits = D(facts.credits_total) or Decimal(0)
    if subs and None not in subs and total is not None and gst is not None:
        exp = sum(subs) + gst - credits
        if not close(exp, total, cfg):
            flags.append(Flag("C08", WARN, "current_charges_total",
                              f"Subtotals {sum(subs)} + GST {gst} − credits {credits} = {exp}, "
                              f"but current charges say {total}."))

    # C09 GST ≈ 5% of pre-GST charges
    if total is not None and gst is not None:
        pre = total - gst
        if not close(gst, pre * cfg.gst_rate, cfg):
            flags.append(Flag("C09", WARN, "gst_amount",
                              f"GST {gst} is not {cfg.gst_rate * 100}% of {pre}."))

    # C11 confidence
    if facts.confidence != "high":
        flags.append(Flag("C11", WARN, "confidence",
                          f"Model confidence is {facts.confidence}; check every number. "
                          "Quote is marked DRAFT."))
    # C13 credits
    if credits:
        flags.append(Flag("C13", INFO, "credits_total",
                          f"Credits of {credits} are excluded from the comparison."))

    # C18 identical site ids on a dual-fuel bill
    ids = {s.commodity: s.site_id for s in facts.services if s.site_id}
    if len(ids) == 2 and len(set(ids.values())) == 1:
        flags.append(Flag("C18", WARN, "services", "Electricity and gas share the same site ID."))
    return flags


def has_block(flags: list[Flag], for_enrolment: bool = False) -> bool:
    return any(f.severity == BLOCK and (for_enrolment or not f.enrol_only) for f in flags)
