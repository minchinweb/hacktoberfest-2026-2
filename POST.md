---
title: "Only two lines on an Alberta power bill matter. A local model finds them."
published: false
tags: devchallenge, hf26challenge, gemma, python
---

<!--
DRAFT NOTES (delete before publishing)
Everything below is written from what exists in the repo today. Items still to fill, all marked [TODO]:
  1. Demo GIF/video (phone photo -> review screen with one flagged field -> customer quote).
  2. "My First User": the timed session in SPEC §13 has NOT happened. No timings or verdict are invented here.
  3. Agent session slug for the {% agent_session %} tag.
  4. Re-check the UCA link and any regulatory claim the day you publish.
Stay anonymous: no company, partner or deal names. The demo brand and offers are fictional.
-->

*This is a submission for the Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle.*

## What I Built

I run a small electricity and natural gas retailer in Alberta. Every new customer starts the same way: someone looks at their current bill, works out whether switching would save them money, and then types the site IDs, name and address into an enrolment form. A referral partner can bring in hundreds of homes at a time, and many of those homes have two sites, one for power and one for gas. That is a lot of squinting at photographs of bills.

**bill2quote** turns a photo or PDF of a utility bill into two things:

1. **A one-page savings comparison** the customer can read: what this bill cost on their current plan, what the same usage would cost on our offer, and the difference. If their current plan is cheaper, the page says that, plainly.
2. **An enrolment-ready row** with site ID(s), service address, name and current retailer, plus the partner's referral code.

A vision model running on my own machine reads the bill. Plain Python checks what it read, does every calculation, and writes the outputs. A person confirms the numbers on a review screen before any customer-facing quote exists.

The insight that makes this tractable: of the dozens of lines on an Alberta bill, only two belong to the retailer, the **energy charge** and the **admin fee**. Delivery, riders and the local access fee are set by regulators and municipalities and are the same whichever retailer you pick ([Utilities Consumer Advocate, "How to read your bill"](https://ucahelps.alberta.ca/understanding-your-bill.aspx)). So the comparison is two lines, plus GST on the difference. The arithmetic is easy. Reading the bill is the hard part.

## Demo

[TODO: GIF or short video. A printed-and-photographed bill reads best on camera: phone photo, then the review screen with one amber field, then the customer view.]

Every bill in this post and in the repo is synthetic. The retailer, people, addresses, account numbers and site IDs are all invented.

## Code

https://github.com/minchinweb/hacktoberfest-2026-2

Python 3.11+, FastAPI, Jinja2, pypdfium2, Pillow, Ollama. No build step, no database, no hosted API. `bill2quote batch DIR` for the office, `bill2quote serve` for the phone.

## How I Built It

### The model reads. The code checks.

The rule I wrote at the top of the spec and kept to: the model transcribes what is printed and never calculates, converts or corrects anything. A suspect number is flagged and shown to a person, never quietly fixed.

The model gets one request per bill with every page attached, a JSON schema, temperature 0 and thinking off. Every field in the schema is required but nullable, so the output is either complete or rejected, and "I couldn't read it" is an answer the model is allowed to give. That is a lesson from Week 1: letting a small model omit fields produced confident, plausible, wrong output.

Then 19 deterministic checks run, each returning a flag with a severity. A few of them:

- **C01:** does the energy charge equal usage × rate? A small gap is a warning, since a tiered rate can explain it. More than three times apart blocks the quote, since nothing explains that.
- **C04:** do the meter readings add up to the usage?
- **C06:** is the rate plausible for its unit? (This one catches ¢ vs $ mix-ups and blocks the quote.)
- **C07 / C17:** is the site ID 13 digits starting with 00 (electricity, never 000) or 000 (gas), and is it *not* the account number? Some account numbers are also 13 digits, so a model can easily put the wrong one in the wrong box.
- **C12:** is anything quote-critical missing?
- **C19:** does the comparison itself make sense? If the two retailer lines on the offer come out three times higher or lower than on the current plan, a number was misread, and the quote is not shown.

Blocking flags stop a customer quote. Warnings must be acknowledged on the review screen with a tick box. Every edit a reviewer makes is logged with the model's value, the new value and the time.

### How it did

I generated eight synthetic bills across three layouts (a one-page table, a summary plus detail page, and a two-column dual-fuel statement) with varied wording, plus a Pillow "phone photo" of one of them: rotated, in perspective, shadowed, JPEG at quality 60. Ground truth comes from the same data that rendered each bill. Two models, same prompt, same bills:

| Model | Bills with every quote-critical field right | Valid output | Seconds per bill |
|---|---|---|---|
| Gemma 4 e4b | 5 of 8 | 8 of 8 | about 9 |
| Qwen3-VL 8b | 6 of 8 | 6 of 8 | about 73 |

"Quote-critical" means usage, days, energy charge or rate, and admin fee. Field-level accuracy was 94% for Gemma and 97% for Qwen, which sounds great and is exactly the wrong number to look at: one wrong digit in the one field that matters is a wrong quote.

**One failure, told straight.** On the synthetic gas bill, Gemma put the usage (37.49 GJ) into the energy charge field. The correct charge was $183.33. A quote built from that would have told a customer they'd lose $117.70 by switching, when they'd have saved money. Nothing about it looks wrong at a glance. What caught it was check C01: *charge 37.49 ≠ usage 37.49 × rate 4.89 = 183.33*. (At that point C01 was only a warning; it now blocks the quote, see below.) Two more from the same run: on the phone photo it read usage as 30.937 kWh, which looks like the previous meter reading (30,937) with the comma taken for a decimal point, and C04 flagged it; on another bill it labelled a 12.05 ¢/kWh rate as dollars, and C06 blocked the quote. Two more bills came back with site IDs one digit short: Gemma read `0010099000016` as `001009900016`, and the gas ID on the same bill lost a zero the same way, apparently dropping one from a run of zeros. C07 blocked enrolment on both, with *site ID is not 13 digits starting with 00*. A truncated ID would be quietly accepted by any tool that only checks the field is filled in. Three of eight bills needed a human fix. That is why the review screen is the product, not an afterthought.

### Real phone photos

I then printed the bills and photographed them with a Pixel 7 on a table: some tilted, one with my finger over part of the page, bill 03 as two photos. Seven bills, scored separately from the table above, which still includes the simulated photo. Same prompt, same models:

| Model | Bills with every quote-critical field right | Valid output | Seconds per bill |
|---|---|---|---|
| Gemma 4 e4b | 3 of 7 | 7 of 7 | about 10 |
| Qwen3-VL 8b | 5 of 7 | 5 of 7 | about 72 |

This is the hardest test so far, and Gemma lost ground: 3 of 7, against 5 of 8 on the clean PDFs. On the bills with a different label wording it often put values against the wrong row. My guess is that the tilt of the page shifts the right-hand values against the left-hand labels, but I haven't tested that. Its four failures were bills 02, 05, 06 and 08. On a second read of those four, a check fired on every one: C06 blocked the gas bill, where a usage of 37.49 had landed in the rate field, C12 blocked the one where usage came back empty, and the others raised C01, C03 or C04 warnings (for example *meter reads give 0.700 kWh but usage says 700.0*). Qwen got both of its misses by returning nothing usable: on bills 05 and 08 the JSON was cut off.

**A warning was not enough.** While recording the demo on bill 02, I fixed the fields the checks had flagged and left two that weren't, usage (the m³ figure had landed in the GJ field) and the energy charge, then ticked the box and confirmed. The page cheerfully said my current plan was cheaper by $4,072.21, or $47,947 over a year. C01 had only been a warning, and I had acknowledged it. So I changed two things. A C01 gap of more than 3× now blocks the quote, and a new check (C19) refuses any comparison whose two sides are more than 3× apart. The same data now gets a red field on the review screen and no quote. And the quote page has an **Edit numbers and re-run** link that reopens the form with the saved values and the offer choices, so fixing a number and re-running the comparison takes seconds.

Qwen scored one bill better, but it always thinks (the `think: false` flag has no effect on it), it is about eight times slower, and two of its eight outputs were empty. I suspect the thinking ate the whole 8,192-token budget, but I haven't proved it. I kept Gemma as the default, but less comfortably than before: on the real photos Qwen is two bills ahead (5 of 7 against 3 of 7), though still only seven bills and 8 times slower. Gemma is fast enough to use at a kitchen table, and when it is wrong the checks have caught it every time I looked. That is the trade I'm making, and more bills could change it. The reader is one config value (`models.extract`) and `bill2quote eval --model X` scores any Ollama vision model on the same bills, so swapping in a better model when one is released, or a locally fine-tuned one, means changing a setting and re-running the eval, not touching the code.

### Honest limits

- **Every bill here is synthetic**, printed and photographed. None is a real customer's bill. Real retailer layouts are the next test and I expect them to be harder. Seven photos is a small sample. The photos are in `samples/photos/` with the location data stripped, and the results are in `docs/eval/photos/`.
- A frontier hosted model would probably read a blurry phone photo better. That is a real cost of staying local.
- The 12-month estimate for gas is a rough days-scaling, labelled as such on the page, until I add heating-degree-day data. Per-bill numbers get top billing for that reason.
- The offers in the demo are made-up round numbers. This is not a statement about any real price.

## Why Does Open Innovation Matter?

- **The data is sensitive in a specific way.** A bill carries a name, a service address, an account number and a site ID. A site ID is the meter's identity in the market and most of what's needed to enrol a site. Sending a stack of those to a hosted API is the wrong default for a business that handles thousands. Here the bills never leave the machine.
- **No meter running.** Reading a thousand multi-page bills costs nothing per page, and re-reading them after a prompt change is free. The eval above would have been a line item on an API invoice.
- **The model is a config value, and I can measure it.** Swapping Gemma for Qwen was one flag, and the table above is the result. The choice of model rests on numbers, not on a vendor's say-so.
- **Room to specialise.** Alberta bills are a narrow layout family. That is the kind of place a small model could later be fine-tuned. Not this week, but it's possible, which is the point.

## My Agent Session

{% agent_session [TODO: slug] %}

I built this with Claude Code from a written spec, working milestone by milestone. [TODO: one or two sentences on a moment worth pointing at. A candidate from the session: the first Qwen run scored 0 of 8 because it returned empty output, and the fix was a token budget, not a prompt change.]

## My First User

[TODO: the SPEC §13 session. Not yet done, so nothing is claimed here.]

My first user is me, as the retailer: internal use by the buyer, which is a weaker test than an outside customer. I'll time a quote and enrolment record done the current way for two printed synthetic bills, then the same two plus the planted-error bill with the tool, and report both timings, every hesitation, whether the planted error was caught, and my honest answer to "would the business pay for this, and how?"

- Manual, per bill: [TODO]
- With bill2quote, per bill: [TODO]
- Planted error caught: [TODO]
- Verdict as the buyer: [TODO]

## Prize Categories

**Best Use of Gemma.** Gemma 4 e4b is the default reader. It reads every bill in the eval to a valid result and takes about nine seconds a bill on my Windows laptop. I report where it fails and how the checks catch it, and I report that Qwen3-VL scored one bill higher. I'm not claiming any other category.

---

### Author's Notes

I drafted this post with AI help, as I did the earlier entries, and edited it myself. The software was built with Claude Code from a spec I wrote with it. All numbers above come from runs saved in the repo (`docs/eval/`).
