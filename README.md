# The Promise Problem

**An analysis of 99,441 orders on the Olist Brazilian marketplace (Sep 2016 – Oct 2018).**

🔗 **[Interactive dashboard](https://varadharajanv0310.github.io/olist-promise-problem/)** · **[Analysis report](https://varadharajanv0310.github.io/olist-promise-problem/report/)** · **[Notebook](notebook/olist_promise_problem.ipynb)**

Olist promises customers a delivery date, then beats it by a median of twelve days. That sounds like
broken forecasting. It isn't — it's a correctly-priced insurance policy, and this analysis shows why
the obvious recommendation (tighten the estimates) would destroy value.

---

## Headline findings

**Satisfaction is a cliff, not a slope.** Delivering fifteen days early instead of three buys 0.10
stars. Slipping from three days late to seven costs 1.45 stars and triples the 1-star rate. Past day
seven the damage saturates — there is no further downside, and no way back.

| Delivery vs. promise | orders | mean score | 1-star rate |
|---|---|---|---|
| 15d+ early | 29,767 | 4.31 | 6.9% |
| 3–7d early | 12,657 | 4.21 | 7.0% |
| 0–3d **late** | 2,677 | 3.75 | 14.2% |
| 3–7d **late** | 1,823 | **2.30** | **53.7%** |
| 15d+ **late** | 1,394 | 1.72 | 69.0% |

**The delay is line-haul, not sellers.** Of the 19.4 extra median days on a late order, 17.0 is
carrier transit and only 1.3 is seller handoff. Payment approval is noise.

**A finding that did not survive its own test.** 37% of all 1-star reviews are written *before* the
parcel arrives, because the survey fires at `estimated_delivery_date + 2 days`. That looked like a
measurement artifact depressing scores. It isn't: a regression discontinuity at the two-day trigger
returns an effect of +0.15 stars (SE 0.19), and the 95% CI rules out anything above 0.52 against a
raw gap of 1.50. The anger is real, not an artifact — so the fix is not to delay the survey. But the
text tells a second story: those reviews are 53% *"não recebi"* versus 16% for post-delivery ones.
The survey isn't a broken measurement, it's an **unread distress signal** — 8,446 customers reporting
non-receipt while the order is still in flight and still recoverable.

---

## Repository

```
scripts/
  00_extract_xlsx.py      stream the delivered workbook into CSVs
  01_profile.py           structural + quality profile
  02_survey_timing.py     survey-timing deep dive
  03_rdd_robustness.py    regression discontinuity, placebos, donut check
  10_build_base.py        PHASE 1 — cleaning + the analytical base table
reports/                  text output from each stage
notebook/                 the submission notebook
PLAN.md                   end-to-end plan
```

## Data

Not committed. The [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
is published under CC BY-NC-SA. Place the nine CSVs in `data/raw/`, then:

```bash
python scripts/10_build_base.py
```

This writes `data/processed/orders_analytical.parquet` — one row per order, 65 columns — which every
downstream analysis reads from.

## Method notes

- Statistics are written in numpy rather than statsmodels: `statsmodels` 0.14.4 fails against
  `scipy` ≥ 1.16 (`_lazywhere` was removed), and the notebook has to run unattended in Colab.
- Time series are restricted to **Jan 2017 – Aug 2018**. The 2016 head (4, 0, 1 orders/month) and the
  Sep/Oct 2018 tail (16, 4) are export artifacts; plotting the raw range invents a collapse at both ends.
- Review scores are bimodal (57% fives, 12% ones), so driver analysis models **P(1-star)** rather
  than the mean.
