# bill2quote

*Hacktoberfest 2026 Open-Source AI Challenge, Week 2: Side Hustle.*

A photo or PDF of an Alberta utility bill in; an honest one-page savings comparison and an
enrolment-ready record out. A local open-weight vision model (via Ollama) **reads** the bill.
Plain Python **checks** the arithmetic, does the money math and writes the outputs. A person
confirms the numbers on a review screen before any customer-facing quote exists.

Only two lines on the bill belong to the retailer: the energy charge and the admin fee. Delivery,
riders and the local access fee are the same whichever retailer the customer picks, so savings
come only from those two lines (plus GST on the difference). If the customer's current plan is
cheaper, the page says so.

## Data note

**Every bill in this repo is synthetic.** The retailer, people, addresses, account numbers and
site IDs (`0010099…` electricity, `0000099…` gas) are fictional, and the demo offers are made-up round numbers. No real bill or
customer data is committed (`data/`, `private/` and `*.real.*` are gitignored). Accuracy numbers
below come from synthetic layouts only, including phone photos of printed samples. Real retailer
layouts are the next test.

## Install

```powershell
python -m venv .venv; .\.venv\Scripts\activate
pip install -e ".[dev]"
ollama pull gemma4:e4b
ollama pull qwen3-vl:8b        # optional, for comparison
bill2quote init                 # writes config.toml and data/
bill2quote doctor               # Ollama, models, image input, PDF rendering
```

## Use

```powershell
bill2quote read samples/01_elec_clean.pdf      # BillFacts JSON
bill2quote batch samples/                       # read + check + staff quote for each bill
bill2quote eval samples --model gemma4:e4b --model qwen3-vl:8b
bill2quote serve                                # http://127.0.0.1:8000/?ref=PARTNER
```

The web app listens on `127.0.0.1` by default. To use it from a phone, bind to your LAN address and
set a shared password; it refuses to listen elsewhere without one:

```powershell
$env:BILL2QUOTE_PASSWORD = "something-long"
bill2quote serve --host 0.0.0.0
```

LAN or Tailscale only. Never port-forward it.

Flow: snap bill → review (flagged fields highlighted with the reason; every edit is logged) →
quote (customer view masks site IDs and shows no flags; staff view shows everything; print to PDF)
→ add to `data/enrolments.csv`. The old account number is never exported.

## How it is split

| Model reads | Python decides |
|---|---|
| Transcribes what is printed, nulls for anything unreadable | 20 checks (C01–C20) on the arithmetic, units, IDs and the plausibility of the comparison |
| Never calculates or corrects | All money math in `Decimal`; blocking flags stop a quote |

## Eval (synthetic bills, 8 total)

See `docs/eval/eval.md`. Gemma 4 e4b: 5/8 bills with every quote-critical field right, about 9 s
per bill. Qwen3-VL 8b: 6/8, about 78 s per bill, and 2 of 8 produced no valid output because its
thinking used up the token budget. Every misread was caught by a check (a meter reading taken as
usage, a ¢/$ unit mix-up, a missing usage value) rather than reaching a customer quote.

## Known gaps

- Gas annual estimate is days-scaled with a loud "ROUGH" note until Edmonton heating-degree-day
  normals are added to `config.toml` (`annualize.hdd_monthly`); the method is implemented and tested.
- Not yet done: Docker, first-user write-up, demo recording, the post.

## Licence

MIT.
