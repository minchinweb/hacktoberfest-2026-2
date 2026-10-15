# First user: the retailer, on the seven printed bills

**Who:** me, as the retailer. This is internal use by the buyer, which is a weaker test than an outside
customer, but the retailer is the one who would pay. The bills are the seven printed synthetic ones
(01, 02, 03, 05, 06, 07, 08). All are in one basic layout with no extra text, which makes them easy and
fast to read by eye.

## Timings

| | Time | Per bill |
|---|---|---|
| Manual review of 7 bills (3:17:27 to 3:35:11) | 17 min 44 s | about 2 min 32 s |
| bill2quote, bill 01 (read cleanly) | about 1 min 42 s | |
| bill2quote, bill 02 (misread badly, many fields fixed) | about 4 min 37 s | |
| bill2quote, mean of those two | | about 3 min 10 s |

Tool time is measured from the screen recordings, from tapping **Snap bill** to the enrolment list
showing the new row. Login is not counted. About 20 to 25 seconds of each run is waiting for the read
(upload plus the model).

How far to trust these numbers:

- **The tool runs were demo recordings, not a stopwatch session.** They include viewing both quote
  views and the print-to-PDF dialog.
- **Only two bills were timed with the tool.** Bill 07 (the planted error) was not run live. A third
  recording, an earlier take of bill 02 that ended on a wrong quote, never reached the enrolment step
  and is left out.
- **Bill 02 is the hard case.** It is a photo of a print with a mislabelled energy line, and the model
  put several values on the wrong row. Correcting them is most of its 4 min 37 s.
- **The manual time was a review of the bills.** It is not directly comparable with a tool run that
  also produces the quote and the enrolment row.

On these bills the tool was not faster. Bill 01 took less than the manual average, and bill 02 took
about twice as long.

## What I caught that the tool did not

- **A $25 promotional discount on one bill**, which will need a conversation with the client. The tool
  does read credits and lists them as an informational note (C13), and leaves them out of the
  comparison. It does not tell you to raise them with the client.
- **That none of the bills carried a balance forward.** A carried-forward balance is a credit-risk
  signal: we might not want the customer, or at least need to talk about it. The tool does not look at
  the previous balance at all. It is not in the schema.

## What the tool flags that I did not see

I did not see any of the issues the tool would have flagged. On these seven bills the tool raises the
planted $20 error in the energy charge on 07 (C01), the estimated meter read on 05 (C15), and the
credit on 06 (C13, informational).

## Verdict as the buyer

The main benefit for me is that, once properly configured, the tool can deal with different bill
formats. This test used one basic format with no extra text, which made manual review easy and fast, so
the manual numbers above are the optimistic case. The tool's value on these bills was in the checks,
not in speed.

Two more benefits I expect:

- **A properly formatted quote for the client.** Today my quote is scribbles on the customer's own bill.
  The tool produces a clean one-page comparison (customer view, print or save as PDF).
- **A record for follow-up.** Each enrolment is written to a CSV, with the partner code, the bill and the
  offer, so it can be tracked in a CRM for follow-up and to confirm that the enrolment went through.
  Today the tool only writes the CSV. It has no CRM connection and does not track whether an enrolment
  succeeded.

What is missing before a partner could use it alone:

1. Read the previous balance and flag a carried-forward balance for a credit discussion.
2. Treat a promotional credit as something to raise with the client, not just a note.
3. Test on real retailer layouts, which are harder than these.
4. Connect the enrolment record to a CRM and track whether each enrolment succeeded.

Would the business pay for it, and how: *not yet answered. To be filled in by the owner.*
