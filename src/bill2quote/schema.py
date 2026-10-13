"""BillFacts: what the model transcribes (SPEC §8.1).

Every field is required and nullable, so the output is either complete or rejected.
The model never calculates; it copies what is printed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RateUnit = Literal["cents_per_kWh", "dollars_per_kWh", "dollars_per_GJ"]
AdminBasis = Literal["per_day", "per_month", "per_bill"]


class Service(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commodity: Literal["electricity", "gas"]
    site_id: str | None
    plan_name: str | None
    period_start: str | None
    period_end: str | None
    days: int | None
    usage: float | None
    usage_unit: Literal["kWh", "GJ"] | None
    usage_m3: float | None
    gas_conversion_factor: float | None
    meter_previous: float | None
    meter_current: float | None
    meter_multiplier: float | None
    estimated_read: bool | None
    energy_rate: float | None
    energy_rate_unit: RateUnit | None
    energy_charge: float | None
    admin_fee: float | None
    admin_fee_rate: float | None
    admin_fee_basis: AdminBasis | None
    delivery_total: float | None
    service_subtotal: float | None


class BillFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retailer: str | None
    customer_name: str | None
    service_address: str | None
    account_number: str | None
    bill_date: str | None
    current_charges_total: float | None
    gst_amount: float | None
    credits_total: float | None
    services: list[Service]
    confidence: Literal["high", "medium", "low"]
    unreadable: list[str] = Field(default_factory=list)


def json_schema() -> dict:
    """JSON Schema for Ollama's `format` parameter."""
    return BillFacts.model_json_schema()
