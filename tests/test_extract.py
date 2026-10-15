import json

from PIL import Image

from bill2quote import extract
from bill2quote.schema import BillFacts


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_extract_accepts_fenced_json(monkeypatch):
    payload = {
        "message": {
            "content": "```json\n" + json.dumps({
                "retailer": "Demo",
                "customer_name": "A B",
                "service_address": "1 Main St",
                "account_number": "1234567890123",
                "bill_date": "2026-09-02",
                "current_charges_total": 103.95,
                "gst_amount": 4.95,
                "credits_total": None,
                "services": [{
                    "commodity": "electricity",
                    "site_id": "0000099000011",
                    "plan_name": "Plan",
                    "period_start": "2026-08-01",
                    "period_end": "2026-08-31",
                    "days": 30,
                    "usage": 500.0,
                    "usage_unit": "kWh",
                    "usage_m3": None,
                    "gas_conversion_factor": None,
                    "meter_previous": 1000.0,
                    "meter_current": 1500.0,
                    "meter_multiplier": 1.0,
                    "estimated_read": False,
                    "energy_rate": 10.0,
                    "energy_rate_unit": "cents_per_kWh",
                    "energy_charge": 50.0,
                    "admin_fee": 9.0,
                    "admin_fee_rate": 0.30,
                    "admin_fee_basis": "per_day",
                    "delivery_total": 40.0,
                    "service_subtotal": 99.0,
                }],
                "confidence": "high",
                "unreadable": [],
            }) + "\n```"
        }
    }
    monkeypatch.setattr(extract.httpx, "post", lambda *args, **kwargs: FakeResponse(payload))

    facts, meta = extract.extract([Image.new("RGB", (64, 64), "white")], "test-model", "http://localhost:11434")

    assert isinstance(facts, BillFacts)
    assert facts.customer_name == "A B"
    assert meta["model"] == "test-model"
