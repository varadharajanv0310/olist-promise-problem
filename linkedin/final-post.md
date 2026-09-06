# LinkedIn post

**Attach:** `figures/q2_the_cliff.png`, or a carousel of `q2_the_cliff.png` →
`q2_promise_vs_actual.png` → `q6_odds_ratios.png` → `q7_risk_scorer.png` → a dashboard screenshot.

**Tag Gradient Learning using the @ picker** so it links — a typed mention doesn't register.

---

## The post

🚀 I took part in the **Data Analytics Hackathon** conducted by **@Gradient Learning**.

My project: **The Promise Problem** — an analysis of ~100,000 real orders from Olist, a Brazilian
marketplace that connects small merchants to the major platforms.

📊 **The problem**
Olist has two years of data spread across nine tables — orders, order items, payments, reviews,
customers, products, sellers, geolocation and a category translation table — and no consolidated view
connecting them. Leadership knows customer satisfaction varies. Nobody can say what actually drives
it, or where to spend effort to improve it.

💡 **My approach**
I reduced all nine tables to one analysis-ready row per order: 99,441 rows and 65 columns, with every
cleaning decision made once and documented.

That cleaning mattered more than I expected. Reviews contain 827 duplicate IDs across 555 orders
surveyed more than once. 775 orders have no line items at all — and they're overwhelmingly the
cancelled and unavailable ones, so an inner join silently deletes the platform's worst outcomes from
every revenue figure. The geolocation table holds ~53 rows per zip prefix, so joining it directly
multiplies your data by fifty. And the first and last months of the export contain 4 and 1 orders
respectively, which invents a collapse at both ends of any time series.

🔧 **The technical work**
→ Aggregated to order grain with guarded joins that assert the row count never changes
→ Collapsed geolocation to one point per zip prefix, clipped to Brazil's bounding box, then computed
haversine seller→customer distance for 98.7% of orders
→ Modelled **P(1-star)** rather than mean score, because the distribution is bimodal (57% fives, 12%
ones) — a mean averages two populations that barely overlap. Logistic regression fitted by IRLS in
numpy, with standardised terms so odds ratios compare directly
→ Ran a **regression discontinuity** to test one of my own findings, with placebo cutoffs and a
donut specification as robustness checks
→ Built the promise model as **gradient-boosted quantile regression**, split by time rather than
randomly, with seller-history features computed from the training window only so nothing leaks
backward. Every input is knowable at checkout
→ Benchmarked each seller against their own category × distance cells rather than the platform
average, so a furniture seller shipping across the country isn't punished for geography

Everything is written in numpy and scikit-learn — no statsmodels, since version 0.14.4 fails to
import against scipy ≥ 1.16, which is what Colab currently ships.

🔍 **Data & insights**
Review scores are flat across every early-delivery bucket, then collapse past the promised date.
Fifteen days early instead of three is worth **+0.10 stars**; three days late to seven costs
**−1.45** and triples the 1-star rate.

Olist pads every estimate by about twelve days, which looks like poor forecasting but is really
protection against that asymmetry. Between 2017 and 2018 they cut the promise from 39 days to 13
while actual delivery improved by under 4 — and their late rate tripled.

Of the ~19 extra days on a late order, **17 are carrier transit** and 1.3 is seller handoff.

Delivery failure explains **48.8%** of 1-star reviews. The other 51.2% arrived on time, so it's the
biggest single lever rather than the whole problem.

The largest single driver in the model wasn't lateness — it was orders split across multiple sellers,
at 5× the odds. Olist stores one delivery date per order, so a multi-parcel order is marked complete
when the first box arrives.

🛠️ **What I built**
→ A cleaning pipeline and Colab notebook that runs end to end
→ A model that sets a delivery promise per order instead of one flat buffer: **47% fewer late
deliveries at the same average promise length**, measured on 25,352 held-out orders
→ A seller scorecard ranking sellers by stars lost against their own benchmark
→ An interactive dashboard and a written report, both deployed

**Biggest learning:** the most useful part wasn't finding results, it was testing them. Three
recommendations that seemed obvious didn't survive being checked, and leaving them out made the final
set much stronger.

**What's one analysis project where testing your assumption changed the answer?**

#DataAnalytics #DataAnalyticsHackathon #DataScience #Analytics #BuildWithData #ProductSpace

---

## First comment (post it a little later)

Dashboard → https://varadharajanv0310.github.io/olist-promise-problem/
Report → https://varadharajanv0310.github.io/olist-promise-problem/report/
Code → https://github.com/varadharajanv0310/olist-promise-problem
