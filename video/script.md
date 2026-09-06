# Video script — full walkthrough

Screen-record and talk over it. Cues in *italics* are what to have on screen; everything else is what
to say. Read it once out loud first so it sounds spoken rather than read.

**Note on length:** this covers everything — dashboard, report, notebook and repo. Read straight
through it runs about four and a half minutes. If you need to hit three, the sections marked
**[CUT IF SHORT]** come out cleanly without breaking the thread.

---

## The problem

*Dashboard hero. Let the loading screen play.*

"Olist is a Brazilian marketplace integrator. Small merchants sign one contract and sell through the
big platforms, Olist's partners handle delivery, and once the order arrives the customer rates it one
to five stars.

Leadership has two years of that — about a hundred thousand orders across nine tables. Orders, items,
payments, reviews, customers, products, sellers, geolocation. What they don't have is anything
connecting them. They know satisfaction varies. Nobody can say what actually drives it.

That's the question I took on. And the headline is right here: Olist promises delivery in twenty-three
days and actually delivers in ten. My first instinct was that their forecasting was broken."

## The approach

*Scroll slowly through the stat strip.*

"I reduced all nine tables to one analysis-ready row per order — ninety-nine thousand rows, sixty-five
columns — with every cleaning decision made once and documented.

That cleaning mattered more than I expected. The reviews table has eight hundred duplicate IDs. Seven
hundred and seventy-five orders have no line items at all, and they're overwhelmingly the cancelled
ones — so an inner join silently deletes the platform's worst outcomes from every revenue figure. And
the geolocation table holds about fifty-three rows per postcode, so joining it directly multiplies
your data fiftyfold.

Then I worked through the six core questions, and tested each conclusion before keeping it rather
than after."

## The finding everything rests on

*Section 01 — the cliff. Pause here.*

"This is the chart the whole analysis hangs from.

Satisfaction doesn't decay as delivery slips. It holds almost perfectly flat right up to the promised
date — then it collapses.

Arriving fifteen days early instead of three buys you a tenth of a star. Slipping from three days
late to seven costs you one and a half stars, and triples the one-star rate. Past about day seven the
damage is done; it doesn't get worse, and there's no way back.

So those twelve days of padding aren't sloppy forecasting. They're insurance against a wildly
asymmetric downside."

*Section 02 — the timeline.*

"And the obvious recommendation — tighten your estimates — has already been tried. Over nineteen
months Olist cut the promise from thirty-nine days to thirteen while actual delivery improved by under
four. Their late rate tripled. This chart is the post-mortem on the advice I nearly gave."

## The recommendation

*Section 03 — the frontier. Drag the slider slowly, land on 95.*

"So if you shouldn't shorten the promise and you shouldn't lengthen it, what do you actually do?

You stop making one promise for the whole platform. Right now Olist applies the same twelve-day
buffer to a hundred-and-sixty-kilometre São Paulo order and a two-thousand-four-hundred-kilometre
order to Pará.

Instead, predict each order's delivery time at checkout and promise a chosen risk level.

*Land the slider. Let −47% sit on screen.*

Same twenty-one-day average promise. Forty-seven percent fewer late deliveries. That's measured on
twenty-five thousand orders the model never saw — trained on everything up to April 2018, tested on
May through August, with seller history built only from the training window so nothing leaks.

The buffer isn't cut. It's moved off the orders that never needed it."

## Keeping it honest

*Section 04 — the attribution bar.*

"One thing I want to be straight about. Delivery explains forty-nine percent of one-star reviews. Not
all of them. Half of the worst reviews arrived on time and the customer was unhappy anyway. It's the
biggest single lever, not the whole problem — and a submission that claimed otherwise would be
overselling."

*Section 05 — lead time.*

"Where the delay actually lives: of the roughly nineteen extra days on a late order, seventeen are
carrier transit and about one is the seller. This isn't a seller-speed problem."

## The rest of the dashboard

**[CUT IF SHORT — this whole section]**

*Scroll through 06, 07, 08, 09.*

"The seller queue benchmarks every seller against their own category and shipping distance, so a
furniture seller shipping across the country isn't punished for geography, then ranks them by stars
lost — volume times shortfall. That's who you call first.

The geography section shows why distance matters: São Paulo holds forty-two percent of customers but
seventy-one percent of sellers, and every delivery metric moves with distance from that cluster.

The driver model ranks what actually causes a one-star review. And the biggest single factor isn't
lateness — it's orders split across multiple sellers, at five times the odds. Olist stores one
delivery date per order, so a multi-parcel order gets marked complete, and surveyed, when the first
box arrives. The customer is asked to rate a finished order while holding half of one.

And the last section shows what the review text says — 'never arrived' runs at thirty percent among
one-star reviews and one percent among five-star."

## The report and the code

**[CUT IF SHORT — compress to one sentence]**

*Click through to the report. Scroll to the "three recommendations this analysis killed" box.*

"The written report walks the same argument in full, with the method and the limitations.

The section I'd point at is this one — three recommendations the analysis killed. Tighten the
estimates: the asymmetry says no, and Olist already ran that experiment. Delay the review survey,
because thirty-seven percent of one-star reviews are written before the parcel arrives: I tested that
as a regression discontinuity and the effect came back at plus fifteen hundredths of a star with a
standard error of nearly two — indistinguishable from zero. And focus on your worst-rated sellers,
which just targets small sellers with noisy averages.

*Switch to the GitHub repo.*

Everything's reproducible. The notebook runs top to bottom, the cleaning pipeline, the models and
thirty figures are all in the repo, and every number regenerates end to end."

## Close

*Back to the dashboard, section 06 — the seller queue.*

"So: don't change how fast you ship. Change what you promise, per order. Fix the multi-parcel bug,
because it's a notification change rather than a capital project. And when you're ready to act on
sellers — this is the list, ranked by how much each one is actually costing you.

Thanks for watching."

---

## Recording notes

- **1080p minimum.** The mono type is small and blurs below that.
- **Hard-refresh before you start** so the loading screen plays — it's four seconds and it sets the tone.
- **Don't read numbers off the screen.** Say them, and let the screen confirm.
- Two takes, not ten. Slightly unpolished and confident beats over-rehearsed.
- If the live walkthrough gets fiddly, the fallback is these figures in order:
  `q2_the_cliff` → `q2_promise_vs_actual` → `q7_risk_scorer` → `q12_attribution` → `q6_multiseller`
  → `q8_seller_scorecard`.
