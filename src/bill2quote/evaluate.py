"""Field-level accuracy against *.truth.json (SPEC §11)."""

from __future__ import annotations

import json
from pathlib import Path

from . import extract, ingest
from .config import Config
from .schema import BillFacts, Service

TOP_FIELDS = ["retailer", "customer_name", "service_address", "account_number", "bill_date",
              "current_charges_total", "gst_amount", "credits_total"]
SERVICE_FIELDS = [f for f in Service.model_fields if f != "commodity"]


def norm(v):
    if isinstance(v, str):
        return " ".join(v.lower().split())
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), 4)
    return v


def same(a, b) -> bool:
    return norm(a) == norm(b)


def score(pred: BillFacts, truth: dict) -> dict:
    """Per-field correctness for one bill. Services are matched by commodity."""
    p = pred.model_dump()
    fields: dict[str, bool] = {k: same(p[k], truth[k]) for k in TOP_FIELDS}
    psv = {s["commodity"]: s for s in p["services"]}
    critical = True
    site_ok = True
    for ts in truth["services"]:
        c = ts["commodity"]
        ps = psv.get(c)
        for f in SERVICE_FIELDS:
            fields[f"{c}.{f}"] = ps is not None and same(ps[f], ts[f])
        if ps is None:
            critical = site_ok = False
            continue
        ok = lambda f: same(ps[f], ts[f])
        critical &= (ok("usage") and ok("days") and ok("admin_fee")
                     and (ok("energy_charge") or ok("energy_rate")))
        site_ok &= ok("site_id")
    if len(psv) != len(truth["services"]):
        critical = False
    return {"fields": fields, "critical": critical, "site_id": site_ok}


def bills_in(directory: Path) -> list[tuple[Path, dict]]:
    out = []
    for t in sorted(directory.glob("*.truth.json")):
        stem = t.name.removesuffix(".truth.json")
        src = next((p for ext in (".pdf", ".jpg", ".jpeg", ".png")
                    if (p := directory / f"{stem}{ext}").exists()), None)
        if src:
            out.append((src, json.loads(t.read_text(encoding="utf-8"))))
    return out


def run(directory: Path, models: list[str], cfg: Config, log=print) -> dict:
    bills = bills_in(directory)
    result: dict = {}
    for model in models:
        rows = []
        for src, truth in bills:
            pages = ingest.load_pages([src], cfg.models["max_pages"], cfg.models["max_image_side"])
            row = {"bill": src.name}
            try:
                facts, meta = extract.extract(pages, model, cfg.models["ollama_host"],
                                             cfg.models["num_ctx"], cfg.models["num_predict"])
                s = score(facts, truth)
                n_ok = sum(s["fields"].values())
                row.update(valid=True, seconds=meta["seconds"], critical=s["critical"],
                           site_id=s["site_id"], fields_ok=n_ok, fields_total=len(s["fields"]),
                           wrong=[k for k, v in s["fields"].items() if not v])
            except extract.ExtractError as e:
                row.update(valid=False, seconds=None, critical=False, site_id=False,
                           fields_ok=0, fields_total=0, wrong=[], error=str(e))
            log(f"{model} {src.name}: critical={row['critical']} site={row['site_id']} "
                f"fields={row['fields_ok']}/{row['fields_total']} {row['seconds']}s")
            rows.append(row)
        result[model] = rows
    return result


def markdown(result: dict) -> str:
    lines = ["| Model | Bills read | Quote-critical | Site ID | Fields | Avg s/bill |",
             "|---|---|---|---|---|---|"]
    for model, rows in result.items():
        n = len(rows)
        valid = sum(r["valid"] for r in rows)
        fo = sum(r["fields_ok"] for r in rows)
        ft = sum(r["fields_total"] for r in rows) or 1
        secs = [r["seconds"] for r in rows if r["seconds"] is not None]
        lines.append(f"| {model} | {valid}/{n} | {sum(r['critical'] for r in rows)}/{n} | "
                     f"{sum(r['site_id'] for r in rows)}/{n} | {fo / ft:.1%} | "
                     f"{(sum(secs) / len(secs)) if secs else 0:.1f} |")
    lines += ["", "Per bill (quote-critical correct?):", "",
              "| Bill | " + " | ".join(result) + " |", "|---|" + "---|" * len(result)]
    names = [r["bill"] for r in next(iter(result.values()))]
    for i, name in enumerate(names):
        cells = ["yes" if result[m][i]["critical"] else "NO" for m in result]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
