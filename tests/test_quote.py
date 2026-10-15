import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from bill2quote import config
from bill2quote.annualize import hdd_share
from bill2quote.quote import build_quote, cents
from bill2quote.schema import BillFacts

CFG = config.load("config.example.toml")


def truth(name):
    return BillFacts.model_validate(json.loads(Path(f"samples/{name}.truth.json").read_text()))


def test_hand_calculated_electricity():
    # 612 kWh, $70.32 energy + $9.00 admin = $79.32 now.
    # Offer: 612 x 0.0899 = 55.0188 + 30 days x 0.30 = 9.00 -> 64.0188. Diff 15.3012 x 1.05.
    q = build_quote(truth("01_elec_clean"), CFG)
    s = q.services[0]
    assert s.offer_energy == Decimal("55.0188")
    assert cents(s.diff_pre_gst) == Decimal("15.30")
    assert cents(s.diff) == Decimal("16.07")


def test_electricity_annual_is_days_scaled():
    s = build_quote(truth("01_elec_clean"), CFG).services[0]
    assert s.annual_usage == Decimal(612) * 365 / 30
    assert "typical month" in s.annual_method


def test_gas_without_hdd_is_loudly_rough():
    gas = build_quote(truth("02_gas_clean"), CFG).services[0]
    assert gas.annual_method.startswith("ROUGH")


def test_override_annual_usage():
    q = build_quote(truth("01_elec_clean"), CFG, annual_override={"electricity": Decimal(7000)})
    assert q.services[0].annual_usage == Decimal(7000)


def test_already_cheaper_is_negative():
    q = build_quote(truth("08_already_cheaper"), CFG)
    assert q.total_diff < 0
    assert all(s.diff < 0 for s in q.services)


def test_credits_are_excluded_not_counted():
    q = build_quote(truth("06_credit_dual_fuel"), CFG)
    assert q.credits_excluded == Decimal("25.0")


def test_hdd_shares_over_a_year_sum_to_one():
    hdd = [900, 750, 650, 400, 200, 80, 30, 50, 200, 450, 700, 880]
    total = hdd_share(date(2026, 1, 1), 365, hdd, Decimal("0.15"))
    assert abs(total - 1) < Decimal("0.0001")


def test_c19_blocks_an_implausible_comparison():
    from bill2quote.checks import BLOCK
    from bill2quote.quote import quote_flags
    facts = truth("02_gas_clean")
    facts.services[0].usage = 981.4  # the m3 figure read as GJ: the mistake seen in a real photo
    flags = quote_flags(build_quote(facts, CFG), CFG)
    assert [f.id for f in flags] == ["C19"] and flags[0].severity == BLOCK


def test_c19_is_silent_on_every_sample_bill():
    from bill2quote.quote import quote_flags
    for name in ("01_elec_clean", "02_gas_clean", "03_dual_fuel_2page", "05_estimated_read",
                 "06_credit_dual_fuel", "07_inconsistent", "08_already_cheaper"):
        assert quote_flags(build_quote(truth(name), CFG), CFG) == [], name
