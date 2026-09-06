# LinkedIn — the single post

**Attach:** `figures/q2_the_cliff.png` as the primary image. If you post a carousel, follow it with
`q2_promise_vs_actual.png` then a screenshot of the dashboard hero.

**Tag Gradient Learning with the @ picker**, not plain text — an unlinked mention doesn't register.

**Post it once, then reply to your own post** with the dashboard and repo links about an hour later.
LinkedIn suppresses reach on posts with outbound links in the body; putting them in the first
comment avoids that and still gets them in front of anyone who reads.

---

## The post

🚀 I just finished the **Data Analytics Hackathon** conducted by **@Gradient Learning**, and the most
useful thing I did was prove myself wrong.

The dataset: ~100,000 real orders from Olist, a Brazilian marketplace.

The first thing I found looked like a smoking gun. Olist promises delivery in a median of **23 days**
and actually delivers in **10**. Twelve days of padding. Obvious conclusion: their forecasting is
broken, tighten the estimates.

So before recommending that, I checked what happens when they miss.

📉 Arriving 15 days early instead of 3 → **+0.10 stars**
📉 Slipping from 3 days late to 7 → **−1.45 stars**, and the 1-star rate triples

That padding isn't incompetence. It's insurance against a wildly asymmetric downside.

Then I found the part that settled it: **Olist already ran this experiment.** Over 19 months they cut
the promise from 39 days to 13 while actual delivery improved by under 4. Their late rate tripled.

I killed a second hypothesis the same way. 37% of all 1-star reviews are written *before the parcel
arrives*, because the survey fires two days after the estimated date. That looked like a measurement
artifact depressing their scores — an easy fix. A regression discontinuity at the two-day trigger
returned **+0.15 stars, standard error 0.19**. Indistinguishable from zero. The anger was real. The
fix would have done nothing.

So what actually works?

**Stop making one promise for the whole platform.** Olist applies the same 12-day buffer to a 160 km
São Paulo order and a 2,400 km order to Pará. Predict each order's delivery time and promise a chosen
risk level instead.

✅ Same 21-day average promise
✅ **47% fewer late deliveries**
✅ Tested on 25,352 orders the model never saw

The buffer isn't cut. It's moved off the orders that never needed it.

The thing I'll actually carry forward: the three recommendations I *deleted* were more valuable than
most of the ones I kept. "Tighten the estimates," "delay the survey," "fix your worst-rated sellers" —
all intuitive, all wrong, and all cheap to test before saying out loud.

**What's a recommendation you almost shipped before the data talked you out of it?**

#DataAnalytics #DataAnalyticsHackathon #DataScience #Analytics #BuildWithData #ProductSpace

---

## First comment (post ~1 hour later)

Full write-up and the interactive dashboard, if you want to move the risk slider yourself:

📊 Dashboard → https://claude.ai/code/artifact/875ea937-031e-4599-8b37-538f111444d0
📋 Report → https://claude.ai/code/artifact/8fb42cc0-e0f0-4cfa-a478-b7ac857468c6
💻 Code → https://github.com/varadharajanv0310/olist-promise-problem

Notebook, cleaning pipeline, the regression discontinuity, the risk model and 30 figures are all in
the repo — every number regenerates end to end.
