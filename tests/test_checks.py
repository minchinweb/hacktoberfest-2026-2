from bill2quote import config
from bill2quote.checks import BLOCK, INFO, WARN, check_bill, has_block
from bill2quote.schema import BillFacts

CFG = config.load("config.example.toml")


def service(**kw):
    base = dict(
        commodity="electricity", site_id="0010099000011", plan_name="Plan",
        period_start="2026-08-01", period_end="2026-08-31", days=30,
        usage=500.0, usage_unit="kWh", usage_m3=None, gas_conversion_factor=None,
        meter_previous=1000.0, meter_current=1500.0, meter_multiplier=1.0,
        estimated_read=False, energy_rate=10.0, energy_rate_unit="cents_per_kWh",
        energy_charge=50.0, admin_fee=9.0, admin_fee_rate=0.30, admin_fee_basis="per_day",
        delivery_total=40.0, service_subtotal=99.0,
    )
    base.update(kw)
    return base


def bill(svc=None, **kw):
    base = dict(
        retailer="Demo", customer_name="A B", service_address="1 Main St",
        account_number="1234567890123", bill_date="2026-09-02",
        current_charges_total=103.95, gst_amount=4.95, credits_total=None,
        services=[service(**(svc or {}))], confidence="high", unreadable=[],
    )
    base.update(kw)
    return BillFacts.model_validate(base)


def ids(facts):
    return {f.id for f in check_bill(facts, CFG)}


def test_clean_bill_has_no_flags():
    assert check_bill(bill(), CFG) == []


# C01
def test_c01_fires_on_mismatch():
    assert "C01" in ids(bill({"energy_charge": 80.0}))


def test_c01_far_apart_blocks_but_modest_gap_only_warns():
    sev = lambda charge: next(f.severity for f in check_bill(bill({"energy_charge": charge}), CFG)
                              if f.id == "C01")
    assert sev(80.0) == WARN      # 1.6x: could be a tiered rate
    assert sev(5.0) == BLOCK      # a tenth: a number was misread
    assert sev(500.0) == BLOCK    # ten times


def test_c12_usage_must_be_positive():
    assert "C12" in ids(bill({"usage": 0.0}))


def test_c01_missing_value_is_silent():
    assert "C01" not in ids(bill({"energy_charge": None}))


# C02
def test_c02_fires_and_accepts_inclusive():
    assert "C02" in ids(bill({"days": 20}))
    assert "C02" not in ids(bill({"days": 31}))


def test_c02_missing_dates():
    assert "C02" not in ids(bill({"period_start": None}))


# C03
def test_c03_fires():
    assert "C03" in ids(bill({"admin_fee": 12.0}))


def test_c03_missing():
    assert "C03" not in ids(bill({"admin_fee_rate": None}))


# C04
def test_c04_fires():
    assert "C04" in ids(bill({"meter_current": 1800.0}))


def test_c04_multiplier():
    assert "C04" not in ids(bill({"meter_current": 1250.0, "meter_multiplier": 2.0}))


def test_c04_missing():
    assert "C04" not in ids(bill({"meter_previous": None}))


# C05
def gas(**kw):
    d = dict(commodity="gas", usage=10.0, usage_unit="GJ", usage_m3=263.0,
             gas_conversion_factor=0.038, energy_rate=4.0, energy_rate_unit="dollars_per_GJ",
             energy_charge=40.0, meter_previous=None, meter_current=None)
    d.update(kw)
    return d


def test_c05_pass():
    assert "C05" not in ids(bill(gas()))


def test_c05_product_mismatch():
    assert "C05" in ids(bill(gas(usage_m3=400.0)))


def test_c05_factor_out_of_range():
    assert "C05" in ids(bill(gas(gas_conversion_factor=0.38, usage_m3=26.3)))


def test_c05_missing():
    assert "C05" not in ids(bill(gas(usage_m3=None)))


# C06 / C14
def test_c06_cents_dollars_mixup_blocks():
    flags = check_bill(bill({"energy_rate": 0.10}), CFG)  # $/kWh printed, labelled cents
    assert any(f.id == "C06" and f.severity == BLOCK for f in flags)


def test_c06_in_range_ok():
    assert "C06" not in ids(bill({"energy_rate": 0.10, "energy_rate_unit": "dollars_per_kWh",
                                  "energy_charge": 50.0}))


def test_c14_unknown_unit():
    assert "C14" in ids(bill({"energy_rate_unit": None}))


# C07 / C17
def test_c07_bad_site_id_blocks_enrolment_only():
    flags = check_bill(bill({"site_id": "12345"}), CFG)
    f = next(x for x in flags if x.id == "C07")
    assert f.severity == BLOCK and f.enrol_only
    assert not has_block(flags) and has_block(flags, for_enrolment=True)


def test_c07_prefix_depends_on_commodity():
    # electricity needs 00..., gas needs 000...
    assert "C07" in ids(bill({"site_id": "0123456789012"}))
    assert "C07" not in ids(bill({"site_id": "0012345678901"}))
    assert "C07" in ids(bill({"site_id": "0002345678901"}))  # electricity is never 000
    b = bill(services=[service(**gas(site_id="0012345678901"))])
    assert "C07" in ids(b)
    b = bill(services=[service(**gas(site_id="0001234567890"))])
    assert "C07" not in ids(b)


def test_c07_missing_site_id():
    assert "C07" in ids(bill({"site_id": None}))


def test_c17_site_equals_account():
    assert "C17" in ids(bill({"site_id": "0123456789012"}, account_number="0123456789012"))


def test_c17_distinct():
    assert "C17" not in ids(bill())


# C08 / C09
def test_c08_fires():
    assert "C08" in ids(bill(current_charges_total=150.0))


def test_c08_missing_total():
    assert "C08" not in ids(bill(current_charges_total=None))


def test_c09_fires():
    assert "C09" in ids(bill(gst_amount=9.0, current_charges_total=108.0))


def test_c09_missing():
    assert "C09" not in ids(bill(gst_amount=None))


# C10 / C15
def test_c10_info():
    flags = check_bill(bill({"days": 60, "period_end": "2026-09-30"}), CFG)
    assert any(f.id == "C10" and f.severity == INFO for f in flags)


def test_c15_estimated_read():
    assert "C15" in ids(bill({"estimated_read": True}))


# C11 / C13
def test_c11_low_confidence_warns():
    flags = check_bill(bill(confidence="low"), CFG)
    assert any(f.id == "C11" and f.severity == WARN for f in flags)


def test_c13_credits_info():
    assert "C13" in ids(bill(credits_total=5.0, current_charges_total=98.95))


# C12
def test_c12_missing_each_critical_field():
    for field in ("usage", "days"):
        assert "C12" in ids(bill({field: None}))
    assert "C12" in ids(bill({"energy_charge": None, "energy_rate": None}))
    assert "C12" in ids(bill({"admin_fee": None, "admin_fee_rate": None}))


def test_c12_blocks_quote():
    assert has_block(check_bill(bill({"usage": None}), CFG))


# C16
def test_c16_duplicate_period():
    flags = check_bill(bill(), CFG, seen={("0010099000011", "2026-08-31")})
    assert any(f.id == "C16" for f in flags)
    assert not any(f.id == "C16" for f in check_bill(bill(), CFG, seen=set()))


# C18
def test_c18_same_site_both_fuels():
    b = bill(services=[service(), service(**gas(site_id="0010099000011"))])
    assert "C18" in ids(b)
