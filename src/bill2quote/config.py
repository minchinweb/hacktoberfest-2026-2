"""TOML config loading with defaults (SPEC §8.2)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "models": {
        "extract": "gemma4:e4b",
        "compare": ["gemma4:e4b", "qwen3-vl:8b"],
        "ollama_host": "http://localhost:11434",
        "max_pages": 4,
        "max_image_side": 2000,
        "num_ctx": 16384,
        "num_predict": 8192,
    },
    "brand": {"name": "Demo Retail Energy Co.", "phone": "", "email": "", "logo": ""},
    "tax": {"gst_rate": "0.05"},
    "checks": {
        "site_id_regex": {"electricity": r"^00[1-9]\d{10}$", "gas": r"^000\d{10}$"},
        "elec_rate_cents_range": [2, 40],
        "gas_rate_dollars_range": [1, 20],
        "gas_factor_range": [0.030, 0.045],
        "period_days_range": [20, 40],
        "money_tolerance": "0.02",
        "pct_tolerance": "0.005",
        "implausible_ratio": "3",
    },
    "annualize": {"gas_base_fraction": "0.15", "hdd_monthly": []},
    "offer": [],
}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Offer:
    id: str
    commodity: str
    name: str
    energy_rate: Decimal  # $/kWh or $/GJ
    admin_fee_per_day: Decimal
    term_months: int
    terms_url: str = ""


@dataclass
class Config:
    raw: dict[str, Any]
    offers: list[Offer] = field(default_factory=list)

    @property
    def models(self) -> dict:
        return self.raw["models"]

    @property
    def checks(self) -> dict:
        return self.raw["checks"]

    @property
    def gst_rate(self) -> Decimal:
        return Decimal(self.raw["tax"]["gst_rate"])

    @property
    def money_tol(self) -> Decimal:
        return Decimal(self.checks["money_tolerance"])

    @property
    def pct_tol(self) -> Decimal:
        return Decimal(self.checks["pct_tolerance"])

    @property
    def implausible_ratio(self) -> Decimal:
        return Decimal(self.checks["implausible_ratio"])

    def offer(self, offer_id: str) -> Offer:
        for o in self.offers:
            if o.id == offer_id:
                return o
        raise KeyError(f"unknown offer {offer_id!r}")


def load(path: str | Path | None = None) -> Config:
    """Load `path`, else ./config.toml if present, else ./config.example.toml, else defaults."""
    raw = DEFAULTS
    candidates = [Path(path)] if path else [Path("config.toml"), Path("config.example.toml")]
    for p in candidates:
        if p.exists():
            raw = _merge(DEFAULTS, tomllib.loads(p.read_text(encoding="utf-8")))
            break
        if path:
            raise FileNotFoundError(path)
    offers = [
        Offer(
            id=o["id"],
            commodity=o["commodity"],
            name=o["name"],
            energy_rate=Decimal(str(o["energy_rate"])),
            admin_fee_per_day=Decimal(str(o["admin_fee_per_day"])),
            term_months=int(o["term_months"]),
            terms_url=o.get("terms_url", ""),
        )
        for o in raw.get("offer", [])
    ]
    return Config(raw=raw, offers=offers)
