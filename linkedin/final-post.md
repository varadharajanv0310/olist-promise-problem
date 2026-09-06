# LinkedIn — the post

**Why it's built this way.** Analytics LinkedIn is saturated with "here's my dashboard 🎉". The one
thing almost nobody posts is a **null result** — a finding they killed on purpose. We have three, all
tested, so that's the spine of the post rather than a footnote.

The first two lines are the entire game — everything after them sits behind "…see more". So the hook
is the counterintuitive number, and the hackathon attribution comes in paragraph three where it
costs nothing.

**Attach:** `figures/q2_the_cliff.png`. If you post a carousel: the cliff → `q2_promise_vs_actual.png`
→ `q6_multiseller.png` → a screenshot of the dashboard hero.

**Tag Gradient Learning with the @ picker** — a typed mention doesn't register for the bonus.

**Links go in your own first comment**, not the body. LinkedIn suppresses reach on posts with
outbound links.

---

## The post

Olist promises delivery in 23 days. It actually delivers in 10.

My first instinct was "your forecasting is broken — tighten it." That would have been the most
expensive advice I could have given them.

I've spent this week on the **Data Analytics Hackathon** conducted by **@Gradient Learning**,
analysing ~100,000 real orders from the Brazilian marketplace Olist. Here's what changed my mind.

**Satisfaction isn't a slope. It's a cliff.**

Arriving 15 days early instead of 3 → **+0.10 stars**
Slipping from 3 days late to 7 → **−1.45 stars**, and the 1-star rate triples

Those twelve days of "padding" aren't sloppiness. They're insurance against a wildly asymmetric
downside.

Then I found the part that settled it: **Olist already ran this experiment.** Over 19 months they cut
the promise from 39 days to 13 while actual delivery improved by under 4. Their late rate tripled.

The dataset contains the post-mortem on the advice I nearly gave.

**The finding I had to kill**

37% of all 1-star reviews are written *before the parcel arrives* — the survey fires two days after
the estimated date. That looked like a measurement artifact deflating their scores. Easy fix, big
headline.

But that trigger creates a sharp cutoff, which means it can be tested as a regression discontinuity.
The effect came back at **+0.15 stars, standard error 0.19.** Indistinguishable from zero.

The anger was real. The fix would have done nothing. I deleted the recommendation.

**The one that survived**

Stop making one promise for the whole platform. Olist applies the same twelve-day buffer to a 160 km
São Paulo order and a 2,400 km order to Pará.

Predict each order's delivery time and promise a chosen risk level instead:

→ Same 21-day average promise
→ **47% fewer late deliveries**
→ Measured on 25,352 orders the model never saw

The buffer isn't cut. It's moved off the orders that never needed it.

**And one thing I didn't see coming**

The largest single driver of 1-star reviews isn't lateness at all. It's orders split across multiple
sellers — **5× the odds**, and they fail even when delivered on time.

Here's why. Olist stores one delivery date per order. But a multi-seller order ships as several
parcels, so it's marked complete — and the survey fires — when the *first* one arrives. The customer
is asked to rate a finished order while holding half of one.

That isn't a logistics problem. It's a schema problem.

The three recommendations I deleted taught me more than the ones I kept. *Tighten the estimates.
Delay the survey. Fix your worst-rated sellers.* All intuitive, all wrong, and all cheap to test
before saying out loud.

**What's a recommendation you almost shipped before the data talked you out of it?**

#DataAnalytics #DataAnalyticsHackathon #DataScience #Analytics #BuildWithData #ProductSpace

---

## First comment — post it ~45 minutes later

Full write-up, plus an interactive version where you can move the risk slider yourself:

Dashboard → https://claude.ai/code/artifact/875ea937-031e-4599-8b37-538f111444d0
Report → https://claude.ai/code/artifact/8fb42cc0-e0f0-4cfa-a478-b7ac857468c6
Code → https://github.com/varadharajanv0310/olist-promise-problem

The notebook, cleaning pipeline, the regression discontinuity, the risk model and 30 figures are all
in the repo. Every number regenerates end to end.

---

## If you want a shorter variant

Cut the "one thing I didn't see coming" section entirely and end on the buffer result. It loses the
best surprise but lands at ~1,200 characters, which suits a feed that skims. I'd keep it — the schema
bug is the most re-shareable thing in the post.
