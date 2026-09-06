# LinkedIn post

**Attach:** `figures/q2_the_cliff.png`, or a carousel of `q2_the_cliff.png` →
`q2_promise_vs_actual.png` → `q7_risk_scorer.png` → a screenshot of the dashboard.

**Tag Gradient Learning using the @ picker** so it links — a typed mention doesn't register.

---

## The post

🚀 I took part in the **Data Analytics Hackathon** conducted by **@Gradient Learning**.

My project: **The Promise Problem** — an analysis of ~100,000 real orders from Olist, a Brazilian
marketplace that connects small merchants to the big platforms.

📊 **The problem**
Olist has two years of orders, payments, reviews, delivery timestamps and geolocation data across
nine tables, and no consolidated view connecting them. Leadership knows customer satisfaction varies.
Nobody can say what actually drives it, or where to spend effort to improve it.

💡 **My approach**
Reduced all nine tables to one analysis-ready row per order — 99,441 rows, 65 columns — with every
cleaning decision documented. Then worked through the six core business questions, and tested each
conclusion before keeping it rather than after.

🔍 **Data & insights**
Review scores are flat across every early delivery bucket, then collapse past the promised date:
15 days early instead of 3 is worth +0.10 stars, while 3 days late to 7 costs −1.45 and triples the
1-star rate.

Olist pads every estimate by about 12 days, which looks like poor forecasting but is actually
protection against that asymmetry. Between 2017 and 2018 they cut the promise from 39 days to 13
while delivery improved by under 4 days — and their late rate tripled.

Delivery failure explains 48.8% of 1-star reviews. The other 51.2% arrived on time, so it's the
biggest single lever rather than the whole problem.

🛠️ **What I built**
→ A cleaning pipeline and Colab notebook that runs end to end
→ A predictive model that sets a delivery promise per order instead of one flat buffer — 47% fewer
late deliveries at the same average promise length, measured on 25,352 held-out orders
→ A seller scorecard ranking sellers against their own category and distance mix
→ An interactive dashboard and a written report

**Biggest learning:** the most useful part wasn't finding results, it was testing them. Three
recommendations that seemed obvious didn't survive being checked, and leaving them out made the
final set much stronger.

**What's one analysis project where testing your assumption changed the answer?**

#DataAnalytics #DataAnalyticsHackathon #DataScience #Analytics #BuildWithData #ProductSpace

---

## First comment (post it a little later)

Dashboard → https://claude.ai/code/artifact/875ea937-031e-4599-8b37-538f111444d0
Report → https://claude.ai/code/artifact/8fb42cc0-e0f0-4cfa-a478-b7ac857468c6
Code → https://github.com/varadharajanv0310/olist-promise-problem
