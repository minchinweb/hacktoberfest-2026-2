"""Jinja2 rendering of the quote page: customer view and staff view (SPEC §5.4, §10)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .checks import Flag
from .config import Config
from .quote import Quote, ServiceQuote, cents
from .schema import BillFacts

TEMPLATES = Path(__file__).parent / "web" / "templates"
_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))


def money(x) -> str:
    return f"${cents(Decimal(str(x))):,.2f}"


def mask(site_id: str | None) -> str:
    return f"•••••••••{site_id[-4:]}" if site_id and len(site_id) >= 4 else "unknown"


def rate(x: Decimal, sq: ServiceQuote) -> str:
    if sq.commodity == "electricity":
        return f"{x * 100:.2f} ¢/kWh"
    return f"${x:.2f}/GJ"


def render_quote(facts: BillFacts, quote: Quote, flags: list[Flag], cfg: Config,
                 view: str = "customer", partner: str = "", edits: list[dict] | None = None,
                 query: str = "", draft: bool | None = None) -> str:
    if view not in ("customer", "staff"):
        raise ValueError(view)
    return _env.get_template("quote.html").render(
        facts=facts, q=quote, flags=flags, brand=cfg.raw["brand"], view=view, partner=partner,
        edits=edits or [], draft=(facts.confidence != "high") if draft is None else draft, today=date.today().isoformat(),
        money=money, mask=mask, rate=rate, query=query)
