"""Generate the synthetic sample bills and their ground truth (SPEC §12).

Seeded and deterministic. Everything here is fictional: retailer, people, addresses,
account numbers and site IDs (0000099...). Truth is built from the same numbers that are
rendered, so it is right by construction.

    python samples/make_samples.py
"""

from __future__ import annotations

import json
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent
CENT = Decimal("0.01")
GST = Decimal("0.05")
W, H = letter


def q(x: Decimal, places: str = "0.01") -> Decimal:
    return x.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def money(x) -> str:
    return f"${q(Decimal(str(x))):,.2f}"


# ---------------------------------------------------------------- data

LABELS = {
    "plain": dict(energy="Energy Charge", admin="Admin Fee", delivery="Delivery Charges",
                  usage="Usage", rate_cents=True),
    "alt": dict(energy="Electricity Supply", admin="Retailer Administration Charge",
                delivery="Transmission & Distribution", usage="Consumption", rate_cents=False),
}


def elec_service(site, usage, rate_cents, days, admin_per_day, delivery, start, end,
                 estimated=False, plan="Variable Plan", use_cents=True):
    usage = Decimal(str(usage))
    rate_cents = Decimal(str(rate_cents))
    charge = q(usage * rate_cents / 100)
    admin = q(Decimal(str(admin_per_day)) * days)
    delivery = Decimal(str(delivery))
    prev = Decimal(random.randint(10000, 60000))
    return dict(
        commodity="electricity", site_id=site, plan_name=plan, period_start=start,
        period_end=end, days=days, usage=float(usage), usage_unit="kWh", usage_m3=None,
        gas_conversion_factor=None, meter_previous=float(prev), meter_current=float(prev + usage),
        meter_multiplier=1.0, estimated_read=estimated,
        energy_rate=float(rate_cents if use_cents else rate_cents / 100),
        energy_rate_unit="cents_per_kWh" if use_cents else "dollars_per_kWh",
        energy_charge=float(charge), admin_fee=float(admin),
        admin_fee_rate=float(admin_per_day), admin_fee_basis="per_day",
        delivery_total=float(delivery), service_subtotal=float(charge + admin + delivery),
    )


def gas_service(site, m3, factor, rate_gj, days, admin_per_day, delivery, start, end,
                plan="Variable Plan"):
    m3 = Decimal(str(m3))
    factor = Decimal(str(factor))
    gj = q(m3 * factor)
    charge = q(gj * Decimal(str(rate_gj)))
    admin = q(Decimal(str(admin_per_day)) * days)
    delivery = Decimal(str(delivery))
    return dict(
        commodity="gas", site_id=site, plan_name=plan, period_start=start, period_end=end,
        days=days, usage=float(gj), usage_unit="GJ", usage_m3=float(m3),
        gas_conversion_factor=float(factor), meter_previous=None, meter_current=None,
        meter_multiplier=None, estimated_read=False, energy_rate=float(rate_gj),
        energy_rate_unit="dollars_per_GJ", energy_charge=float(charge), admin_fee=float(admin),
        admin_fee_rate=float(admin_per_day), admin_fee_basis="per_day",
        delivery_total=float(delivery), service_subtotal=float(charge + admin + delivery),
    )


def make_bill(customer, address, account, bill_date, services, credits=None):
    subs = sum(Decimal(str(s["service_subtotal"])) for s in services)
    cr = Decimal(str(credits)) if credits else Decimal(0)
    gst = q((subs - cr) * GST)
    return dict(
        retailer="Demo Retail Energy Co.", customer_name=customer, service_address=address,
        account_number=account, bill_date=bill_date,
        current_charges_total=float(subs - cr + gst), gst_amount=float(gst),
        credits_total=float(cr) if credits else None, services=services,
        confidence="high", unreadable=[],
    )


# ---------------------------------------------------------------- rendering

def header(c, bill, title="Your Energy Statement"):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, H - 60, bill["retailer"])
    c.setFont("Helvetica", 11)
    c.drawString(50, H - 78, title)
    c.drawRightString(W - 50, H - 60, f"Statement date: {bill['bill_date']}")
    c.drawRightString(W - 50, H - 78, f"Account number: {bill['account_number']}")
    c.drawString(50, H - 110, bill["customer_name"])
    c.drawString(50, H - 124, f"Service address: {bill['service_address']}")


def line(c, x, y, label, value, bold=False, right=None):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
    c.drawString(x, y, label)
    c.drawRightString(right or x + 230, y, value)
    return y - 14


def service_block(c, s, x, y, lab, right):
    kind = "Electricity" if s["commodity"] == "electricity" else "Natural Gas"
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, f"{kind} - {s['plan_name']}")
    y -= 15
    y = line(c, x, y, "Site ID", s["site_id"], right=right)
    y = line(c, x, y, "Billing period", f"{s['period_start']} to {s['period_end']}", right=right)
    y = line(c, x, y, "Days in period", str(s["days"]), right=right)
    if s["commodity"] == "electricity":
        y = line(c, x, y, "Previous meter read", f"{s['meter_previous']:,.0f}", right=right)
        est = " (estimated)" if s["estimated_read"] else ""
        y = line(c, x, y, f"Current meter read{est}", f"{s['meter_current']:,.0f}", right=right)
        y = line(c, x, y, f"{lab['usage']}", f"{s['usage']:,.0f} kWh", right=right)
        unit = "c/kWh" if s["energy_rate_unit"] == "cents_per_kWh" else "$/kWh"
        rate = f"{s['energy_rate']:.2f} {unit}" if unit == "c/kWh" else f"${s['energy_rate']:.4f}/kWh"
    else:
        y = line(c, x, y, "Volume", f"{s['usage_m3']:,.1f} m3", right=right)
        y = line(c, x, y, "Conversion factor", f"{s['gas_conversion_factor']:.4f} GJ/m3", right=right)
        y = line(c, x, y, f"{lab['usage']}", f"{s['usage']:,.2f} GJ", right=right)
        rate = f"${s['energy_rate']:.2f}/GJ"
    y = line(c, x, y, "Rate", rate, right=right)
    y = line(c, x, y, lab["energy"], money(s["energy_charge"]), right=right)
    y = line(c, x, y, f"{lab['admin']} (${s['admin_fee_rate']:.2f}/day)",
             money(s["admin_fee"]), right=right)
    y = line(c, x, y, lab["delivery"], money(s["delivery_total"]), right=right)
    y = line(c, x, y, "Subtotal", money(s["service_subtotal"]), bold=True, right=right)
    return y - 8


def totals(c, bill, x, y, right):
    if bill["credits_total"]:
        y = line(c, x, y, "Promotional credit", f"-{money(bill['credits_total'])}", right=right)
    y = line(c, x, y, "GST (5%)", money(bill["gst_amount"]), right=right)
    y = line(c, x, y, "Current charges", money(bill["current_charges_total"]), bold=True, right=right)
    y = line(c, x, y, "Previous balance", "$0.00", right=right)
    y = line(c, x, y, "Amount due", money(bill["current_charges_total"]), bold=True, right=right)
    return y


def render_a(path, bill, lab):
    """One-page table."""
    c = canvas.Canvas(str(path), pagesize=letter)
    header(c, bill)
    y = H - 160
    for s in bill["services"]:
        y = service_block(c, s, 50, y, lab, 330)
    totals(c, bill, 50, y - 4, 330)
    c.save()


def render_b(path, bill, lab):
    """Summary page plus a detail page."""
    c = canvas.Canvas(str(path), pagesize=letter)
    header(c, bill, "Account Summary")
    y = H - 170
    for s in bill["services"]:
        y = line(c, 50, y, f"{s['commodity'].title()} ({s['period_start']} to {s['period_end']})",
                 money(s["service_subtotal"]), right=400)
    y = totals(c, bill, 50, y - 10, 400)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 60, "Charge detail continues on page 2.")
    c.showPage()
    header(c, bill, "Charge Detail")
    y = H - 160
    for s in bill["services"]:
        y = service_block(c, s, 50, y, lab, 360)
    c.save()


def render_c(path, bill, lab):
    """Two-column dual-fuel statement."""
    c = canvas.Canvas(str(path), pagesize=letter)
    header(c, bill)
    xs = [40, 320]
    for s, x in zip(bill["services"], xs):
        service_block(c, s, x, H - 170, lab, x + 245)
    totals(c, bill, 40, H - 470, 560 - 20)
    c.save()


def pdf_to_image(path: Path) -> list[Image.Image]:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(path))
    return [pdf[i].render(scale=150 / 72).to_pil().convert("RGB") for i in range(len(pdf))]


def phone_photo(pages: list[Image.Image], out: Path, rng: random.Random) -> None:
    """Fake a phone photo: stack pages, rotate ~4 deg, perspective, shadow, JPEG q~60."""
    w = max(p.width for p in pages)
    sheet = Image.new("RGB", (w, sum(p.height for p in pages)), "white")
    y = 0
    for p in pages:
        sheet.paste(p, (0, y))
        y += p.height
    sheet = sheet.rotate(rng.uniform(3, 5), expand=True, fillcolor=(70, 60, 50),
                         resample=Image.BICUBIC)
    sw, sh = sheet.size
    d = int(sw * 0.04)
    coeffs = _persp([(0, 0), (sw, 0), (sw, sh), (0, sh)],
                    [(d, d // 2), (sw - d // 2, 0), (sw, sh - d), (0, sh)])
    sheet = sheet.transform((sw, sh), Image.PERSPECTIVE, coeffs, Image.BICUBIC,
                            fillcolor=(70, 60, 50))
    import numpy as np
    yy, xx = np.mgrid[0:sh, 0:sw]
    t = (0.35 * xx / sw + 0.65 * yy / sh)  # soft diagonal falloff, no hard edges
    gain = 0.78 + 0.22 * t
    arr = np.asarray(sheet, dtype=float) * gain[..., None]
    sheet = Image.fromarray(arr.clip(0, 255).astype("uint8"))
    sheet = sheet.filter(ImageFilter.GaussianBlur(0.8))
    sheet.thumbnail((1600, 2400))
    sheet.save(out, "JPEG", quality=60)


def _persp(dst, src):
    """Coefficients mapping output (dst) points back to input (src) points."""
    import numpy as np
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        rhs += [u, v]
    return np.linalg.solve(np.array(rows, float), np.array(rhs, float)).tolist()


# ---------------------------------------------------------------- the eight bills

def build() -> list[dict]:
    random.seed(2026)
    S = lambda n: f"00000990000{n:02d}"
    a, b = LABELS["plain"], LABELS["alt"]
    bills = []

    def add(name, layout, lab, bill):
        bills.append(dict(name=name, layout=layout, lab=lab, bill=bill))

    add("01_elec_clean", render_a, a, make_bill(
        "Jordan Example", "101 Sample Ave NW, Testville AB T0T 0A1", "4400110022003",
        "2026-09-03", [elec_service(S(11), 612, 11.49, 30, 0.30, 58.40, "2026-08-02", "2026-08-31")]))
    add("02_gas_clean", render_a, b, make_bill(
        "Riley Placeholder", "22 Fiction Rd, Testville AB T0T 0A2", "4400110022004",
        "2026-09-03", [gas_service(S(12), 981.4, 0.0382, 4.89, 31, 0.30, 46.10,
                                   "2026-08-01", "2026-08-31")]))
    add("03_dual_fuel_2page", render_b, a, make_bill(
        "Sam Fakename", "7 Imaginary Cres, Testville AB T0T 0A3", "4400110022005",
        "2026-09-04", [
            elec_service(S(13), 540, 12.05, 30, 0.30, 55.20, "2026-08-02", "2026-08-31"),
            gas_service(S(14), 450.0, 0.0381, 5.15, 30, 0.30, 38.75, "2026-08-02", "2026-08-31")]))
    add("05_estimated_read", render_a, b, make_bill(
        "Alex Notreal", "9 Make-Believe Pl, Testville AB T0T 0A4", "4400110022006",
        "2026-09-05", [elec_service(S(15), 455, 10.99, 29, 0.25, 51.00, "2026-08-02", "2026-08-30",
                                    estimated=True, use_cents=False)]))
    add("06_credit_dual_fuel", render_c, a, make_bill(
        "Casey Madeup", "310 Pretend St, Testville AB T0T 0A5", "4400110022007",
        "2026-09-06", [
            elec_service(S(16), 700, 11.95, 31, 0.30, 62.00, "2026-08-01", "2026-08-31"),
            gas_service(S(17), 600.0, 0.0380, 4.95, 31, 0.30, 41.00, "2026-08-01", "2026-08-31")],
        credits=25.00))
    bad = make_bill(
        "Morgan Invented", "55 Mock Blvd, Testville AB T0T 0A6", "4400110022008",
        "2026-09-07", [elec_service(S(18), 580, 12.30, 30, 0.30, 57.00, "2026-08-02", "2026-08-31")])
    # Planted error: the printed energy charge does not equal usage x rate (C01 must fire).
    bad["services"][0]["energy_charge"] += 20.00
    bad["services"][0]["service_subtotal"] += 20.00
    new_total = q(Decimal(str(bad["services"][0]["service_subtotal"])) * (1 + GST))
    bad["gst_amount"] = float(q(Decimal(str(bad["services"][0]["service_subtotal"])) * GST))
    bad["current_charges_total"] = float(new_total)
    add("07_inconsistent", render_a, a, bad)
    add("08_already_cheaper", render_c, b, make_bill(
        "Taylor Sampledata", "88 Dummy Lane, Testville AB T0T 0A7", "4400110022009",
        "2026-09-08", [
            elec_service(S(19), 650, 8.29, 30, 0.20, 52.00, "2026-08-02", "2026-08-31"),
            gas_service(S(20), 520.0, 0.0383, 3.69, 30, 0.20, 40.00, "2026-08-02", "2026-08-31")]))
    return bills


def main() -> None:
    rng = random.Random(7)
    for spec in build():
        pdf = OUT / f"{spec['name']}.pdf"
        spec["layout"](pdf, spec["bill"], spec["lab"])
        (OUT / f"{spec['name']}.truth.json").write_text(
            json.dumps(spec["bill"], indent=2), encoding="utf-8")
        print("wrote", pdf.name)
        if spec["name"] == "03_dual_fuel_2page":
            photo = OUT / "04_phone_photo_dual_fuel.jpg"
            phone_photo(pdf_to_image(pdf), photo, rng)
            (OUT / "04_phone_photo_dual_fuel.truth.json").write_text(
                json.dumps(spec["bill"], indent=2), encoding="utf-8")
            print("wrote", photo.name)


if __name__ == "__main__":
    main()
