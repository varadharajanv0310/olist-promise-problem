# Olist Hackathon — End-to-End Plan

**Narrative spine:** *Olist doesn't have a delivery problem. It has a promise problem — and it is
throwing away its best early-warning signal.*

Scoring weights: Problem understanding 15 · Cleaning & Analytical 20 · **Insight Quality & Evidence 25**
· LinkedIn 15 · **Recommendations & Visualisation 25**.

---

## Phase 0 — Foundation ✅ DONE

| # | Task | Output |
|---|---|---|
| 0.1 | Extract 9 sheets from the delivered `.xlsx` | `data/raw/*.csv` |
| 0.2 | Structural + quality profile | `reports/profile_01.txt` |
| 0.3 | Test the 4 opening hypotheses | `reports/survey_timing.txt` |
| 0.4 | RD falsification test on survey timing | `reports/rdd_robustness.txt` |

**Established so far**
- ETA is padded ~12 days (median actual 10.2d vs promised 23.2d); 93% arrive early/on time.
- Satisfaction is a **cliff, not a slope**: flat 4.31→4.12 across all early buckets, then
  3.75 → 2.30 → 1.72, saturating by ~day 7 late.
- Late-order delay is **87% carrier transit** (+17.0d of +19.4d), only 6% seller handoff.
- Survey timing has **no causal effect** on score (RD ≈ 0, CI rules out >0.52 stars). The anger is real.
- Pre-delivery 1-stars are 53% "não recebi" vs 16% post-delivery → an unactioned support signal.
- Retention is 3.12% of people / 6.38% of orders.
- Boleto approval lag 29h vs 0.27h card; voucher orders fail to deliver at 7.6% vs 2.9%.

---

## Phase 1 — Cleaning & the analytical base table  ⏳ NEXT

Build **one row per order** (`data/processed/orders_analytical.parquet`), every downstream question
reads from this. `scripts/10_build_base.py`.

**Documented cleaning decisions** (this section *is* the 20% Cleaning score — narrate every choice):
1. Dedupe reviews — 827 dup `review_id`, 555 orders with >1 survey → keep first by creation date.
2. 775 itemless orders → **left** join, retain with null revenue (they are the canceled/unavailable
   ones; an inner join silently deletes the worst-performing orders).
3. Category translation: 71 of 73 covered → hand-add `pc_gamer`,
   `portateis_cozinha_e_preparadores_de_alimentos`.
4. Geolocation → mean lat/lng per zip prefix (52.6 rows/prefix), clipped to Brazil's bounding box
   (lat −34…+6, lng −74…−34) to drop bad readings.
5. Trend window **Jan 2017 – Aug 2018**; the 2016 head and Sep/Oct 2018 tail are export artifacts
   (4, 1, 16 and 4 orders) and must never appear in a time series.
6. `not_defined` payments (3 rows, R$0, 100% undelivered) → flag, exclude from payment mix.
7. Multi-item/multi-seller orders → aggregate deliberately; record `n_items`, `n_sellers`.

**Derived features:** `actual_days`, `promised_days`, `gap_days`, `is_late`, `late_bucket`,
`t_approve`/`t_handoff`/`t_transit`, `order_value`, `freight_total`, `freight_ratio`,
`seller_customer_km` (haversine), `primary_category_en`, `payment_type`, `installments`,
`is_repeat_customer`, `customer_order_seq`, `pre_delivery_review`, `has_comment`.

---

## Phase 2 — The six core questions

| Q | Analysis | Headline chart |
|---|---|---|
| **Q1** Trends | Monthly volume / revenue / AOV / mean score / %1-star. **Lagged demand-vs-quality**: does a volume spike predict a score trough 2–4 weeks later? (Black Friday Nov 2017) | Dual-axis growth vs satisfaction, spike annotated |
| **Q2** Delivery ↔ CSAT | The cliff. Does it hold across category & region or concentrate? Earliness has no upside → **the padding is rational**. Buffer-reduction sensitivity curve. | The cliff + sensitivity curve |
| **Q3** Geography | Haversine seller↔customer distance vs delivery days vs freight vs score. Reframe: not *state*, but **distance from the São Paulo seller cluster**. | State map + distance scatter |
| **Q4** Categories | Volume × price × score portfolio. Which categories are genuinely weak vs merely badly shipped (control for `gap_days`). | 2×2 bubble portfolio |
| **Q5** Payments | The chain: boleto → 29h approval lag → later dispatch → risk. Installments vs order value. Voucher failure rate. | Lag + failure-rate by method |
| **Q6** Root cause | **Logistic model on P(1-star)** — not mean score, the distribution is bimodal (57% fives). Ranked odds ratios → primary vs secondary drivers. Non-delivered statuses broken out as a separate failure mode. | Ranked driver chart |

---

## Phase 3 — Deep dives (pick the two that pay)

- **Repeat customers** — 3.12% repeat rate. Does a bad first order kill the second? This is the slide
  that connects CX to revenue.
- **Seller "Review Damage" scorecard** — `orders × (platform_avg − seller_avg)`, ranking sellers by
  *impact* not badness. Ships as a named top-20 intervention list.
- **Anomalies** — 209-day deliveries, zero-weight products, `not_defined` payments, Dec-2016.

---

## Phase 4 — Deliverables

1. **Colab notebook** — sections named to match the rubric exactly, runs top-to-bottom.
   *Note: avoid `statsmodels` (broken vs scipy ≥1.16); RD/logit written in numpy.*
2. **Analysis report** — published HTML artifact + PDF export.
3. **3-min video** — timed script (~420 words) + slides. Order: problem → approach → insight →
   recommendation.
4. **LinkedIn — 5 posts**, one visual each, each ending on a question:
   - P1 "Olist promises 23 days and delivers in 10. That's not incompetence — it's insurance."
   - P2 The cliff chart — satisfaction doesn't decay, it falls off a ledge at day 3.
   - P3 **"I found a smoking gun. Then I ran the test that killed it."** (the RD null — strongest
     engagement hook of the set, and the most honest)
   - P4 "97% of customers never come back."
   - P5 Recommendations + link to the full report.

---

## Recommendations these roll up to (draft)

1. **Do not tighten the ETA.** Earliness buys ~0.1 stars; lateness costs ~2. The padding is a
   correctly-priced insurance policy. Quantify with the sensitivity curve.
2. **Route pre-delivery 1-stars into a live recovery workflow** — 8,445 customers/yr report
   non-receipt while the order is still recoverable, and Olist files it as historical sentiment.
3. **Attack transit, not sellers** — 87% of excess delay is line-haul, concentrated on long-distance
   routes out of the SP cluster. Regional fulfilment / carrier renegotiation on the worst lanes.
4. **Fix the non-delivery bucket separately** — `unavailable`/`processing` orders score 1.3–1.5★.
   That's an inventory-accuracy problem, not a logistics one.
5. **Seller interventions targeted by review damage**, not by raw rating.
