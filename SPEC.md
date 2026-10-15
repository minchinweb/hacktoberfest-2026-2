# SPEC: bill2quote

**Hacktoberfest 2026 Open-Source AI Challenge, Week 2: Side Hustle**
Repo: `minchinweb/hacktoberfest-2026-2` · local `D:\Code\hacktoberfest-2026-2` · branch `master`
Status: **v1.0 (2026-10-13), ready for handoff.** All direction decisions are made (§17). The two items still open are minor, and the build session can settle them.

---

## 0. Handoff: read this first

You are picking up a planned project. Build it in this repo. These rules outrank everything else in this document:

1. **Deadline: Sun Oct 18, 11:59 PM PDT = Mon Oct 19, 00:59 Edmonton time (06:59 UTC).** Aim to publish Sunday evening. Any commit after the deadline must be listed in the README, or the entry can be disqualified.
2. **This is a new project, built inside the window** (Oct 12–18). The owner's earlier entries, receipt2bean (`hacktoberfest-2026-0`) and roadbean (`hacktoberfest-2026-1`), are references for patterns. Do not copy them wholesale. If you reuse a non-trivial file, credit it in the README.
3. **Never commit a real bill or real customer data.** Put `data/`, `private/` and `*.real.*` in `.gitignore` in the very first commit.
4. **The model reads, the code checks.** The model transcribes what's printed. Python does every calculation, every unit conversion and every judgement. Nothing is ever silently corrected. A suspect value is flagged and shown to a human.
5. **The post is judged hardest.** Writing quality is weighted most heavily. Protect Saturday for the first user (§13) and Sunday for the post (§14).
6. **Stay anonymous.** Never name the owner's company, its partners or any deal, in code, samples, README, this spec or the post. The demo brand, offers and people are all fictional. This repo is public.
7. **Synthetic bills only.** The owner isn't providing real bills. Every test, eval number and screenshot comes from synthetic bills, some of them printed and photographed (§12).

Owner's environment, from earlier weeks: Windows laptop, Python, Ollama with `gemma4:e4b` and `qwen3-vl:8b` already pulled, a Docker host on the home network, and a Pixel 7. Previous posts were drafted with AI help and say so in an "Author's Notes" section. Keep doing that.

**Kickoff prompt for the build session:**

> Read `SPEC.md` in this repo; it is the agreed plan for my Hacktoberfest Week 2 entry. Start at milestone M0 (§15): scaffold the package, `.gitignore`, licence and tests, then go on to M1. Follow §0's rules strictly, especially anonymity and synthetic data only. Commit at each milestone. Ask me before changing scope.

---

## 1. The pitch

The owner runs a small Alberta electricity and natural gas retailer (unnamed in public). Every new customer starts the same way: someone looks at their current utility bill and works out whether switching saves them money. Then someone types the site IDs, name and service address into an enrolment form. Referral partners make this a volume problem: one partner can bring in hundreds of homes, and each home often has two sites (electricity and gas).

**bill2quote** turns a photo or PDF of a utility bill into two things:

1. **An honest one-page savings comparison** the prospect can read: what this bill cost on your current plan, what the same usage would cost on our offer, and the difference. If the difference is negative, the page says so.
2. **An enrolment-ready record** with site ID(s), service address, name and current retailer, plus the referral partner's code for commission tracking.

A local open-weight vision model reads the bill. Plain Python checks the arithmetic, does the math and writes the outputs. A person confirms the extracted numbers on a review screen before any customer-facing quote exists.

## 2. Who pays, and why

- **The retailer (the owner's company).** It pays in staff time today. Fewer hand-keyed site IDs means fewer rejected enrolments, and a faster quote means more conversions. At hundreds of homes from a single partner, minutes per site add up to days or weeks of work. **Measure the real number**: time one manual quote of a synthetic bill, then time the same bill with the tool, and put both in the post.
- **Referral partners and independent energy brokers** in Alberta's competitive market. They need a quote they can produce on a phone, at a kitchen table or a house showing, without learning the bill.
- **Possible business models for the post:** free for the retailer's own partners, because it lifts conversions; a monthly seat for independent brokers; or a one-time setup fee to configure offers and branding. The post should report the owner's verdict as the buyer (§13), not a made-up price.

## 3. Why open: the argument the post must make

- **The data is sensitive in a specific way.** A bill carries a name, a service address, an account number and the site ID(s). A site ID is the meter's identity in the market and most of what's needed to enrol a site with a retailer. Sending a stack of bills to a hosted API is the wrong default for a business that handles thousands of them. Here the bills stay on hardware the business owns.
- **No meter running.** Thousands of multi-page bills cost nothing per page to read locally, and re-reading them after a prompt change is free.
- **Swappable, measurable models.** The model is a config value. The eval harness (§11) scores Gemma 4 and Qwen3-VL on the same bills, so the choice of model rests on numbers.
- **Room to specialise.** A niche layout, Alberta utility bills, is where a small model could later be fine-tuned. This week is out of scope, but the post can say it's possible.
- **Where open was worse.** Say it honestly in the post: a frontier hosted model would probably read a blurry phone photo better.

## 4. Domain notes (Alberta retail energy)

Verified against the Utilities Consumer Advocate (UCA) and EPCOR on 2026-10-13. Re-check anything quoted in the post.

- **Only two lines on the bill belong to the retailer: the energy charge and the administration fee.** Delivery (transmission and distribution) comes from the distributor and is regulated by the AUC. Riders are AUC-approved, and the local access fee (electricity) or municipal franchise fee (gas) is set by the municipality. Those are the same whichever retailer the customer picks. **This is the central simplification, and the central honesty point:** savings come only from the energy rate and the admin fee, plus the GST on the difference.
  Source: UCA, *How to read your bill*: https://ucahelps.alberta.ca/understanding-your-bill.aspx
- **Default electricity rate:** the Rate of Last Resort (RoLR) replaced the RRO on 2025-01-01 and is fixed until 2026-12-31. EPCOR's approved RoLR is 12.01 ¢/kWh. Never hard-code it; it lives in config if it's used at all.
  Source: https://epcor.com/ca/en/news/notices/2024-11-21-regulated-rate-option-to-change-to-the-rate-of-last-resort.html
- **Units:** electricity is billed in kWh, with an energy rate in ¢/kWh or $/kWh. Gas is billed in GJ, converted from m³ by a conversion factor printed on the bill, with an energy rate in $/GJ. An admin fee is usually per day or per month.
- **Dual-fuel bills** (electricity and gas on one statement) are common, so a bill can hold more than one service.
- **Site ID format (confirmed by the owner):** 13 digits, starting with `00` (but never `000`) for electricity, and `000` for natural gas. Keep the format in config as a regex.
- **Watch for account numbers that look like site IDs.** At least one retailer's account number is also 13 digits (ATCO, *How to read your retail energy bill*: https://www.atcoenergy.com/blog/understanding-your-bill). The schema extracts the account number only so the model has somewhere to put it other than `site_id`. It is never exported.
- **GST:** 5% on the bill. Savings shown to a customer include GST on the difference.
- **Total due ≠ this period's charges.** Total due may include a previous balance, so the checks use *current charges*.

## 5. Scope

### MVP (must ship)

1. **Read:** image(s) or PDF in, `BillFacts` JSON out (§8), using an Ollama vision model with schema-constrained output.
2. **Check:** deterministic validation that returns flags (§9).
3. **Review:** a web form showing the bill image beside the extracted fields, with flagged fields highlighted and the reason given. A person corrects and confirms. Every edit is recorded (model value, new value, time).
4. **Quote:** reviewed facts plus an offer from config give a printable HTML page in two views: **customer** (masked site IDs, no flags) and **staff** (everything, including flags). Use the browser's Print to PDF; no PDF library is needed.
5. **Enrol:** append a row to `data/enrolments.csv` and allow download. Collect only the fields needed to enrol.
6. **CLI for batch work:** `batch DIR` runs read, check and staff quote for every bill and prints a summary table.
7. **`doctor`:** checks that Ollama is reachable, the configured models are pulled, a model accepts an image (send a tiny test image), and PDF rendering works.
8. **`eval`:** field-level accuracy against ground truth, per model, written as a Markdown table for the post (§11).
9. **Synthetic sample bills** with ground truth, committed (§12). No real bills anywhere.
10. README, MIT licence, demo GIF or video, and the post draft (`POST.md`).

### Stretch (only after MVP is solid)

- A Dockerfile and compose file for the home Docker host (the app container talks to Ollama over `OLLAMA_HOST`).
- Usage-history extraction: if a bill prints a 12-month usage table, read it and use it for the annual estimate.
- Gas annualisation by heating degree days (§10), if it isn't done in the MVP.
- A purge command (`purge --older-than 30d`) for data retention.
- A model comparison that includes `gemma4:26b`, if it fits on the owner's hardware.
- A pass that uses the PDF text layer as a hint alongside the page images.

### Non-goals

- No market transactions: no enrolment submission and no load-settlement or retailer-switch messages. The output is a CSV for a person to submit.
- No audit of delivery charges or riders.
- No cloud calls with customer data. Every model call goes to a local or LAN Ollama.
- No fine-tuning this week.
- No accounts, multi-user setup or role system. Only a single shared password for LAN use.
- Compliance stays with the business. The tool adds an estimate disclaimer and the offer terms; marketing-rule compliance is the retailer's responsibility.

## 6. User flows

**A. Partner on a phone (the demo flow)**
1. Open `http://<laptop-or-docker-host>:8000/?ref=PARTNER` on the LAN (or over Tailscale). Enter the shared password.
2. Tap **Snap bill** (`<input type=file accept="image/*,application/pdf" capture="environment" multiple>`). Take one or more pages.
3. A "Reading your bill…" page polls every 2 s. Reading takes roughly 5–60 s.
4. Review screen: bill image on the left (pinch to zoom); fields on the right; flagged fields in amber or red with the reason. Fix what's wrong, tick **I checked the flagged fields**, then tap **Confirm**.
5. Quote page: pick an offer from the dropdown and toggle **Customer view**. Print or share the PDF. If a number is wrong, tap **Edit numbers and re-run**: the review form reopens with the saved values and the offer choices kept, and saving it runs the checks and the comparison again. A comparison that fails a blocking check (C19) is not shown at all; the page offers the way back to the form.
6. Tap **Add to enrolment list**.

**B. Office batch**
`bill2quote batch data/inbox/` prints one line per bill: retailer, services, flags, savings per offer. It writes staff quotes. Bills with blocking flags are listed for review in the web UI.

## 7. Architecture and repo layout

```text
photo/PDF ──> ingest ──> extract (Ollama, vision, JSON schema) ──> BillFacts (model)
                                                                     │
                     checks (pure Python) <──────────────────────────┘
                          │ flags
                          v
                 review (web form, human) ──> BillFacts (reviewed) + edit log
                                                    │
                     quote math (pure Python, Decimal)
                          │                          │
                  quote.html (customer/staff)   enrolments.csv
```

```text
pyproject.toml          # Python >= 3.11; console script `bill2quote`
src/bill2quote/
  cli.py                # init, doctor, read, check, quote, batch, serve, eval, (purge)
  config.py             # TOML loading; defaults; validation
  ingest.py             # EXIF transpose, RGB, resize (longest side <= 2000 px), PDF -> PNG via pypdfium2 (~200 DPI), page cap
  schema.py             # pydantic v2 models; JSON Schema export for Ollama `format`
  extract.py            # Ollama /api/chat with images, format=schema, temperature 0, think=false; save raw response + timings
  checks.py             # pure functions -> list[Flag]
  quote.py              # pure money math with Decimal
  annualize.py          # annual usage estimate, method recorded
  store.py              # sha-addressed folders, idempotency, edit log
  render.py             # Jinja2 -> HTML
  enrol.py              # CSV append/read
  evaluate.py           # field accuracy vs *.truth.json
  web/app.py            # FastAPI routes
  web/templates/*.html  # plain HTML + CSS, tiny vanilla JS, no build step
prompts/extract_v1.md   # versioned prompt; version is stored in each facts file
config.example.toml
samples/                # synthetic bills + truth + generator
tests/
docs/                   # demo GIF, screenshots (synthetic bills only), first-user notes
POST.md                 # DEV post draft
```

**Dependencies (keep them small):** pydantic, httpx (or the `ollama` client), pypdfium2, Pillow, Jinja2, FastAPI, uvicorn, python-multipart. For dev and samples: pytest, ruff, and reportlab (sample PDFs). Use `tomllib` from the standard library.

**Data store (gitignored):**

```text
data/bills/<sha12>/
  original-1.jpg | original.pdf
  pages/page-1.png ...
  facts.model.json      # raw model output + model name, model digest, prompt version, seconds
  facts.reviewed.json   # after review, with an `edits` list
  flags.json
  quote-<offer>-<view>.html
data/enrolments.csv
data/log.jsonl
```

Re-uploading the same file is a no-op (same SHA). The same site and billing period showing up again gives an INFO flag.

## 8. Data contracts

### 8.1 BillFacts: what the model returns

Lesson from Week 1: **every field is required in the schema, and `null` is allowed.** That way the output is either complete or rejected. The model transcribes what's printed and never calculates.

```json
{
  "retailer": "string|null",
  "customer_name": "string|null",
  "service_address": "string|null",
  "account_number": "string|null",
  "bill_date": "YYYY-MM-DD|null",
  "current_charges_total": "number|null",
  "gst_amount": "number|null",
  "credits_total": "number|null",
  "services": [
    {
      "commodity": "electricity|gas",
      "site_id": "string|null",
      "plan_name": "string|null",
      "period_start": "YYYY-MM-DD|null",
      "period_end": "YYYY-MM-DD|null",
      "days": "integer|null",
      "usage": "number|null",
      "usage_unit": "kWh|GJ|null",
      "usage_m3": "number|null",
      "gas_conversion_factor": "number|null",
      "meter_previous": "number|null",
      "meter_current": "number|null",
      "meter_multiplier": "number|null",
      "estimated_read": "boolean|null",
      "energy_rate": "number|null",
      "energy_rate_unit": "cents_per_kWh|dollars_per_kWh|dollars_per_GJ|null",
      "energy_charge": "number|null",
      "admin_fee": "number|null",
      "admin_fee_rate": "number|null",
      "admin_fee_basis": "per_day|per_month|per_bill|null",
      "delivery_total": "number|null",
      "service_subtotal": "number|null"
    }
  ],
  "confidence": "high|medium|low",
  "unreadable": ["field names the model could not read"]
}
```

Store model output and reviewed output separately. The quote is only ever built from **reviewed** facts.

### 8.2 Config (`config.toml`)

```toml
[models]
extract = "gemma4:e4b"                 # chosen by eval
compare = ["gemma4:e4b", "qwen3-vl:8b"]
ollama_host = "http://localhost:11434"
max_pages = 4
max_image_side = 2000

[brand]                                 # fictional demo brand (decided)
name = "Demo Retail Energy Co."
phone = ""
email = ""
logo = ""

[tax]
gst_rate = "0.05"

[checks]
site_id_regex.electricity = '^00[1-9]\d{10}$' # confirmed: 13 digits, leading 00, never 000
site_id_regex.gas = '^000\d{10}$'        # confirmed: 13 digits, leading 000
elec_rate_cents_range = [2, 40]
gas_rate_dollars_range = [1, 20]
gas_factor_range = [0.030, 0.045]       # GJ per m3; a deliberately loose sanity range
period_days_range = [20, 40]
money_tolerance = "0.02"
pct_tolerance = "0.005"

[annualize]
gas_base_fraction = "0.15"              # non-heating share of annual gas; an assumption (§17, open item 1)
hdd_monthly = []                        # 12 values, Edmonton climate normals, with the source cited in a comment

[[offer]]
id = "elec-fixed-3y"
commodity = "electricity"
name = "Fixed 3-year"
energy_rate = "0.0000"                  # $/kWh: fictional round demo numbers, never the owner's real offers
admin_fee_per_day = "0.00"
term_months = 36
terms_url = ""

[[offer]]
id = "gas-fixed-3y"
commodity = "gas"
name = "Fixed 3-year"
energy_rate = "0.00"                    # $/GJ
admin_fee_per_day = "0.00"
term_months = 36
terms_url = ""
```

### 8.3 Enrolment CSV columns

`created_at, ref (partner code), bill_sha, customer_name, service_address, commodity, site_id, current_retailer, offer_id, flags_checked`. That is everything enrolment needs from the bill (confirmed by the owner); contact details are collected separately and are out of scope. The old account number is **never** exported.

## 9. Checks: the deterministic half

Each check returns zero or more `Flag(id, severity, field, message)`. Severities:

- **BLOCK:** no customer quote until a reviewer fixes the value.
- **WARN:** the reviewer must tick "I checked the flagged fields".
- **INFO:** shown, nothing required.

| ID | Check | Severity |
|---|---|---|
| C01 | `energy_charge ≈ usage × energy_rate` (within max($0.02, 0.5%)); a small mismatch can mean a tiered or blended rate | WARN; BLOCK when the two are more than `implausible_ratio` (3) times apart, which no tiered rate explains |
| C02 | `days` consistent with the period dates (accept inclusive or exclusive counting) | WARN |
| C03 | `admin_fee ≈ admin_fee_rate × days` when per-day | WARN |
| C04 | Electricity: `(meter_current − meter_previous) × multiplier ≈ usage` | WARN |
| C05 | Gas: `usage_m3 × factor ≈ usage`, and factor within range | WARN |
| C06 | Energy rate inside the plausible range for its unit (catches ¢ vs $ mix-ups) | BLOCK |
| C07 | Site ID matches the regex for its commodity | BLOCK for enrolment only |
| C08 | Σ service subtotals + GST − credits ≈ current charges total | WARN |
| C09 | GST ≈ 5% of pre-GST current charges | WARN |
| C10 | Billing period length within 20–40 days | INFO |
| C11 | Model confidence below `high`: every number marked for review, quote watermarked DRAFT | WARN |
| C12 | Missing any of usage, days, energy charge or rate, admin fee | BLOCK |
| C13 | Credits present: comparison excludes them, and the quote says so | INFO |
| C14 | Unknown rate unit | BLOCK |
| C15 | Estimated meter read | INFO |
| C16 | Same site and period already processed | INFO |
| C17 | `site_id` equals `account_number` (the model put the account number in the wrong field) | BLOCK for enrolment |
| C18 | On a dual-fuel bill, the electricity and gas site IDs are identical | WARN |
| C19 | Quote plausibility: for a chosen offer, the retailer's two lines (energy + admin) cost more than `implausible_ratio` (3) times, or less than 1/3 of, the customer's current two lines. A number was probably misread. Runs on the review screen with the default offers, and again on the quote page with the chosen ones | BLOCK |

Every check gets unit tests with a passing case, a failing case and a missing-value case. The whole checks module runs with no model.

## 10. Quote math

All money uses `Decimal` with exact intermediates. Round half-up to cents for display only.

For each service on the bill and the selected offer for that commodity:

```text
U                = usage (kWh or GJ, converted from the printed unit)
current_energy   = energy_charge as printed
current_admin    = admin_fee as printed
current_rate_eff = current_energy / U                              # effective $/unit
offer_energy     = U × offer.energy_rate
offer_admin      = offer.admin_fee_per_day × days
                   (or per-month fee × days × 12 / 365)
diff_pre_gst     = (current_energy + current_admin) − (offer_energy + offer_admin)
diff             = diff_pre_gst × (1 + gst_rate)                   # positive = customer saves
```

**Annual estimate.** Always label it with its method and its assumptions. The per-bill numbers get top billing on the page.

```text
current_admin_per_day = current_admin / days
offer_admin_per_day   = offer.admin_fee_per_day (or per-month fee × 12 / 365)
annual_diff = ((current_rate_eff − offer.energy_rate) × annual_usage
              + (current_admin_per_day − offer_admin_per_day) × 365) × (1 + gst_rate)
```

`annual_usage`, in order of preference:
1. A value the reviewer entered ("annual usage, if known"), for example from the customer's online account.
2. The sum of 12 months, from several bills for the same site or a printed usage-history table (stretch).
3. **Gas:** scale the bill's usage by heating degree days. The expected share of annual usage for each day is `base/365 + (1 − base) × HDD_day / ΣHDD`, using Edmonton monthly climate normals spread evenly over each month's days. Source the 12 HDD values (Environment and Climate Change Canada, Canadian Climate Normals 1991–2020, an Edmonton station) and cite them in config. If you can't source them, ask the owner rather than inventing them.
4. **Electricity:** `U × 365 / days`, with the note "assumes this bill is a typical month".

Every quote also carries the note "assumes your current rate stays the same for 12 months". A variable-rate plan makes that a snapshot.

**What the customer view shows:**
- This bill: period, usage, your energy rate, your admin fee, and what those two lines cost.
- The same usage on {offer}: the same two lines.
- The difference for this bill (incl. GST), and the 12-month estimate with its method in plain words.
- **What doesn't change:** delivery, riders and the local access fee are the same whichever retailer you choose (cite UCA).
- Offer term, a link to the terms, the date, "Prepared by {partner}".
- Site ID masked to the last 4 digits.
- If `diff < 0`: "On this bill, your current plan is cheaper by $X." The page still renders; no spin.

## 11. Models and evaluation

- **Candidates:** `gemma4:e4b` (already pulled; Gemma 4 accepts image input at every size), `qwen3-vl:8b` (already pulled; it read receipts for receipt2bean in the Weekend Challenge), and `gemma4:26b` (MoE, image input) if it fits.
- **Call settings:** Ollama `/api/chat`, images base64, `format` = the BillFacts JSON Schema, `temperature: 0`, **`think: false`**. In Week 1, Gemma 4 with thinking on returned near-empty or wrong schema output and was 3–6× slower.
- **Multi-page bills:** first try all pages in one request. If eval shows worse results than per-page extraction, extract page by page and merge: later pages fill nulls, and a conflict between pages becomes a WARN flag.
- **Prompt rules** (`prompts/extract_v1.md`): transcribe numbers exactly as printed; never calculate; `null` if not visible; one `services[]` entry per commodity; rate units as printed; "current charges" is not "amount due". Include two or three short worked examples drawn from synthetic bills.
- **`bill2quote eval DIR --model A --model B`:** for each bill, compare against `*.truth.json`:
  - per-field exact match (numbers to printed precision; strings case- and space-normalised)
  - **quote-critical accuracy:** usage, days, energy charge or rate, and admin fee all correct
  - site ID exact match
  - seconds per bill
  - output: Markdown table + a JSON file, ready to paste into the post
- **Default model:** the best quote-critical accuracy wins. On a tie, Gemma, since Best Use of Gemma is a featured category.

## 12. Samples and test data

**All test data is synthetic (decided).** `samples/make_samples.py`, seeded and deterministic, renders bills with reportlab. Use fictional retailers (e.g. "Demo Retail Energy Co."), fictional people and addresses, and site IDs in the real format (13 digits, leading `00` but never `000` for electricity, `000` for gas) that are clearly fake (e.g. `0000099…`, and say in the README that they're fictional). Give every sample a 13-digit account number too, so the site-ID-vs-account-number confusion (C17) actually gets tested. Each bill's `*.truth.json` comes from the same data that rendered it, so the truth is right by construction. **Don't copy any real retailer's branding or layout.**

Because there are no real bills, guard against a model and prompt that only work on one made-up layout:
- **At least three distinct layouts:** (a) a one-page table, (b) a summary page plus a detail page, (c) a two-column dual-fuel statement. Vary the wording too: "Energy Charge" vs "Electricity Supply"; "Admin Fee" vs "Retailer Administration Charge"; ¢/kWh vs $/kWh.
- **Real phone photos of synthetic bills:** print 3–4 sample bills and photograph them with the Pixel 7 (kitchen light, a slight angle, one folded page). Commit those photos with their truth files, since they show no real data. This is the realistic input test, and it makes for an honest demo.

| # | Bill | Exercises |
|---|---|---|
| 1 | Electricity only, clean PDF | happy path |
| 2 | Gas only, clean PDF | m³→GJ, $/GJ |
| 3 | Dual-fuel, 2 pages | two services, page merge |
| 4 | Phone photo of #3 (rotated ~4°, perspective, shadow, JPEG q≈60), via Pillow | realistic input |
| 5 | Estimated meter read | C15 |
| 6 | Promotional credit | C13, C08 |
| 7 | Deliberately inconsistent (energy charge ≠ usage × rate) | C01 must fire |
| 8 | Customer already cheaper than the offer | negative savings page |

**No real bills in this project.** Keep `private/` in `.gitignore` anyway, as a guard in case someone drops a real bill in. The post must say plainly that accuracy was measured on synthetic layouts only, and that real retailer layouts are the next test.

## 13. First user (bonus points)

- **Who (decided):** the owner, as the retailer: internal use by the buyer. Say this plainly in the post. Being your own first user is weaker than an outside customer, but the retailer is the one who pays, so the question "is it worth paying for?" is real.
- **Session (about 30 minutes, on the phone, as if in the field):**
  1. **Manual baseline.** Time a quote and enrolment record done the current way for 2 printed synthetic bills.
  2. **With the tool.** Do the same 2 bills, plus #7 (the planted error), with bill2quote: photo → review → quote → enrol. Note every hesitation, every field corrected by hand, and whether the flag on #7 got caught.
  3. **Answer as the buyer:** minutes saved per site; what that's worth across a partner's volume, in round, non-identifying numbers; would the business pay for this, and how (build vs. buy vs. a monthly tool); what's missing before a partner could use it alone.
- Record the outcome in `docs/first-user.md`. Fix the top one or two issues before recording the demo. If an outside person (a partner, kept unnamed) can try it by Saturday, add them; it's worth more than the self-test.

## 14. The DEV post

- **Template headings** (Week 2 Side Hustle template, in order): What I Built · Demo · Code · How I Built It · Why Does Open Innovation Matter? · My Agent Session · My First User · Prize Categories.
- **Intro line:** *This is a submission for the Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle.*
- **Tags (DEV allows 4):** `devchallenge`, `hf26challenge`, `gemma`, `python`.
- **Prize category:** Best Use of Gemma, if Gemma is the default model or a core part of the eval. Don't claim categories the project doesn't really use.
- **Title ideas:** "bill2quote: a photo of a power bill in, an honest savings quote out" · "Only two lines on an Alberta power bill matter. A local model finds them."
- **Beats:**
  1. Hook: the volume problem. "I run a small Alberta electricity and gas retailer. A referral partner can bring hundreds of homes, and every one starts with a photo of a utility bill." No names, no deal sizes.
  2. The insight: of the many lines on the bill, two belong to the retailer. The math is easy; reading is the hard part. The model reads and Python checks.
  3. Demo: a GIF or short video of phone photo → review screen with one flagged field → customer quote. Synthetic bills only; a printed-and-photographed one reads best on camera.
  4. Who pays: minutes saved per site × sites, plus the owner's verdict as the buyer.
  5. Why open: site IDs and addresses, no per-page fees, swap and measure.
  6. The eval table, plus one failure story told straight (Week 1's "plausible 642 km trip" was the most-read kind of paragraph).
  7. Honest limitations, starting with this one: every number comes from synthetic bills, including phone photos of printed ones. Real retailer layouts are untested.
  8. First user: the owner, as the retailer. Manual vs. tool timings, and the honest buyer's verdict (§13).
  9. An Author's Note on AI use, matching earlier posts.
- **Agent session:** save this build session with DevRelay and embed it with `{% agent_session <slug> %}`.

## 15. Milestones (Edmonton time)

| Day | Milestone | Done when |
|---|---|---|
| Tue Oct 13 | **M0 Spec + scaffold** | SPEC agreed; `pyproject.toml`, package skeleton, `.gitignore`, LICENSE; `pytest` runs green on an empty suite; `bill2quote --help` works |
| Wed Oct 14 | **M1 Read + check** | sample generator makes all 8 bills plus truth; `read` returns valid BillFacts for all 8 with the default model; all checks implemented with tests; `doctor` works |
| Thu Oct 15 | **M2 Quote + batch + eval** | `batch samples/` writes staff quotes; customer view renders and masks site IDs; bill #8 shows negative savings honestly; `eval` table exists for ≥ 2 models; default model chosen |
| Fri Oct 16 | **M3 Web review flow** | phone on the LAN: upload → review (edit + tick) → quote → enrol; edits logged; password required off localhost; Pixel 7 photos of printed samples run end to end and are added to `eval` |
| Sat Oct 17 | **M4 First user + demo** | owner's timed first-user session (§13) done and written up in `docs/first-user.md`; top fixes merged; demo GIF/video recorded |
| Sun Oct 18 | **M5 Publish** | README final (install, run, limits, credits); `POST.md` → DEV post published by about 20:00 MDT; DevRelay session embedded; repo pushed |

If behind schedule, cut in this order: Docker → gas HDD annualisation (fall back to days-scaling with a loud note) → the PDF text-layer hint → the third model in eval. **Never cut** the review step, the checks or the first-user section.

## 16. Risks

| Risk | Mitigation |
|---|---|
| Small vision model misreads small print on phone photos | The review screen and flags are the product. PDFs are preferred, and the post reports photo vs PDF accuracy. |
| Layouts differ by retailer | `services[]` schema; eval per layout; prompt avoids layout-specific wording |
| Annual estimate is disputed | Per-bill numbers first; method and assumptions printed; manual annual-usage override |
| Savings-claim compliance | Disclaimers; negative results shown plainly; no ranking against other retailers |
| Customer data in a demo or repo | Synthetic samples only; `.gitignore` first; no cloud calls |
| Synthetic layouts flatter the model | Three or more layouts with varied wording; real phone photos of printed samples; the post states the limit plainly |
| The anonymous business gets identified | No company, partner or deal names anywhere; fictional brand and offers; check the repo and post for names before publishing |
| A LAN web app gets exposed | Binds to 127.0.0.1 by default; password required otherwise; README says LAN or Tailscale only, never port-forward |
| Five days is short | Cut order in §15; Saturday and Sunday protected |

## 17. Open questions for the owner

**Decided (2026-10-13 planning session):**
- **Project:** bill2quote.
- **Anonymity:** the company and partner stay anonymous everywhere, with a fictional brand and fictional offers.
- **Runs as:** a local web app plus a CLI. Nothing hosted, no partner hosting category.
- **Test data:** synthetic only, including printed-and-photographed samples.
- **Name:** `bill2quote` (package, CLI and repo name in docs).
- **First user:** the owner, using it internally as the retailer (§13).
- **Site IDs:** 13 digits, leading `00` (never `000`) for electricity, `000` for gas.
- **Enrolment needs from the bill:** site ID, name, service address. Contact details are collected separately. The old account number is not needed.

**Still open (the build session decides, or asks the owner):**
1. `gas_base_fraction` (the non-heating share of annual gas use). Default 0.15, labelled as an assumption in the quote, unless the owner gives a better number.
2. The offer numbers for the demo: fictional and round, but plausible for Alberta in 2026. Pick them so that sample #8 comes out negative.

## 18. Alternatives considered

- **Bank-import categoriser for Beancount** (bank CSV → categorised entries, learning from the existing ledger). Useful to the owner and continues the Beancount series, but it's close to the receipt and invoice sorters already submitted this week, and "who pays" is a thin niche.
- **Affiliate commission statements** (supplier sales reports → per-partner commission statements). A real need for the business, but the model only does PDF extraction and the demo is less visual.
- **TabPFN for annual-usage estimates** (featured category). Rejected: its recommended model is under a non-commercial licence, which clashes with a side-hustle theme, and the API route would send customer data off the machine. A two-parameter degree-day method is the standard engineering tool for this job. The post can say so in one line.
- **Hosted on DigitalOcean or Render** (featured categories, plus a `.tech` domain). This would trade the strongest "why open" argument, that bills stay on your hardware, for a category entry. Decided against.
