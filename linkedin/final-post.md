# LinkedIn post

**Fits LinkedIn's 3,000-character limit** (~2,860). No markdown — LinkedIn renders `**bold**` as
literal asterisks, so the copy below is plain text and uses emoji headers and arrows for structure.

**Attach:** `figures/q2_the_cliff.png`, or a carousel of `q2_the_cliff.png` →
`q2_promise_vs_actual.png` → `q6_odds_ratios.png` → `q7_risk_scorer.png` → a dashboard screenshot.

**Tag Gradient Learning using the @ picker** so it links — a typed mention doesn't register.

---

## The post — copy from here

🚀 I took part in the Data Analytics Hackathon conducted by @Gradient Learning.

My project: The Promise Problem — an analysis of ~100,000 real orders from Olist, a Brazilian marketplace connecting small merchants to the major platforms.

📊 The problem
Olist has two years of data across nine tables — orders, items, payments, reviews, customers, products, sellers, geolocation — and no view connecting them. Leadership knows satisfaction varies. Nobody can say what drives it.

💡 My approach
I reduced all nine tables to one row per order: 99,441 rows, 65 columns, every cleaning decision documented. That mattered — reviews carry 827 duplicate IDs, 775 orders have no line items at all (the cancelled ones, so an inner join deletes your worst outcomes), and geolocation holds ~53 rows per zip prefix, so joining it directly multiplies your data fiftyfold.

🔧 The technical work
→ Guarded joins that assert the row count never changes
→ Haversine seller-to-customer distance from aggregated zip centroids, covering 98.7% of orders
→ Modelled P(1-star) rather than mean score: the distribution is bimodal (57% fives, 12% ones), so a mean averages two populations that barely overlap. Logistic regression by IRLS in numpy, standardised so odds ratios compare
→ A regression discontinuity to test one of my own findings, with placebo cutoffs and a donut spec
→ Gradient-boosted quantile regression for the promise model, split by time rather than randomly, seller-history features built from the training window only so nothing leaks

🔍 Insights
Review scores are flat across every early bucket, then collapse past the promised date. Fifteen days early instead of three is worth +0.10 stars. Three days late to seven costs −1.45 and triples the 1-star rate.

Olist pads every estimate by about 12 days. Between 2017 and 2018 they cut the promise from 39 days to 13 while delivery improved by under 4 — and their late rate tripled.

Of the ~19 extra days on a late order, 17 are carrier transit.

Delivery explains 48.8% of 1-star reviews. The other 51.2% arrived on time.

The largest single driver wasn't lateness. It was orders split across multiple sellers, at 5x the odds — Olist stores one delivery date per order, so a multi-parcel order is marked complete when the first box lands.

🛠️ What I built
→ A cleaning pipeline and Colab notebook that runs end to end
→ A model setting a delivery promise per order instead of one flat buffer: 47% fewer late deliveries at the same average promise length, on 25,352 held-out orders
→ A seller scorecard ranking sellers by stars lost against their own benchmark
→ An interactive dashboard and a written report, both deployed

Biggest learning: the useful part wasn't finding results, it was testing them. Three recommendations that seemed obvious didn't survive being checked.

What's one project where testing your assumption changed the answer?

#DataAnalytics #DataAnalyticsHackathon #DataScience #Analytics #BuildWithData #ProductSpace

## — copy to here

---

## First comment (post it a little later)

Dashboard → https://varadharajanv0310.github.io/olist-promise-problem/
Report → https://varadharajanv0310.github.io/olist-promise-problem/report/
Code → https://github.com/varadharajanv0310/olist-promise-problem
