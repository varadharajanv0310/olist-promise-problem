# Olist Hackathon — Plan (revised after all analysis complete)

**Spine:** *Olist doesn't have a delivery problem. It has a promise problem — and it is solving it
with a blunt instrument.*

**The one number:** a risk-based promise delivers **47% fewer late orders at exactly the same
customer-facing promise length.** Not a trade-off — a strictly better operating point.

Scoring: Problem understanding 15 · Cleaning 20 · **Insight Quality 25** · LinkedIn 15 ·
**Recommendations & Visualisation 25**.

---

## ✅ Analysis: COMPLETE

| Stage | Output |
|---|---|
| Phase 0 — profiling, RD falsification | `reports/profile_01.txt`, `rdd_robustness.txt` |
| Phase 1 — cleaning + base table | `orders_analytical.parquet` (99,441 × 65) |
| Q1–Q3 — trends, delivery, geography | `q1_*.txt`, `q2_*.txt`, `q3_*.txt` |
| Q4–Q6 — categories, payments, root cause | `q4_*.txt`, `q5_*.txt`, `q6_*.txt` |
| Multi-seller discovery | `q6_multiseller.txt` |
| Risk scorer | `risk_scorer.txt`, `risk_scores_test.parquet` |
| Seller scorecard | `seller_scorecard.txt`, `seller_scorecard.parquet` |
| Deep dives | `deep_dives.txt` |

**13 figures** in `figures/`.

---

## ⏳ What's left

### A. Two open anomalies (half session) — credibility cheap to buy
1. **Rio de Janeiro.** 394 km median distance (closer than Paraná) but a **13.5% late rate vs
   Paraná's 4.9%** on the platform's 2nd-biggest market. Distance explains every other state; it
   does not explain Rio. Decompose RJ's delay into handoff vs transit to find out whose problem it is.
2. **Feb–Mar 2018.** Worst months in the dataset — 21.4% late, 3.74★ — and *not* a Black Friday
   effect. Was it volume, a specific route, a carrier, or a promise change? Currently unexplained,
   and an unexplained worst-month is a hole a judge will find.

### B. The Colab notebook
Sections named to the rubric, runs top to bottom. Assembled from the existing scripts — the work is
narration, not analysis. **No `statsmodels`** (broken vs scipy ≥1.16); RD and logit are numpy.

### C. The dashboard — a decision tool, not a chart gallery
Everyone will submit a chart gallery. Two interactive pieces nobody else can build, because they
require the modelling to exist first:

- **The Promise Simulator.** A slider over the risk quantile → live mean promise length, late rate,
  and projected review score. Makes the central trade-off something leadership can *feel* rather
  than read. This is the thesis, made operable.
- **The Seller Intervention Queue.** The scorecard, sortable and filterable: 20 named sellers, their
  handoff times, stars lost, and revenue at risk. Turns a recommendation into a worklist.

Plus the static evidence charts. Published as an Artifact → gives us a live URL to link from the
LinkedIn post.

### D. The report
Structured around **falsification, not findings** — the differentiator. It opens with what we
expected, shows the test, and reports what actually held. Includes a section no one else will write:

> **"Three recommendations this analysis killed"**
> 1. *"Tighten the delivery estimates"* — the asymmetry says no, and Olist already ran the
>    experiment: promise cut 39d → 13.4d, late rate tripled.
> 2. *"Delay the review survey"* — 37% of 1-stars are written pre-delivery, but the regression
>    discontinuity returns ≈0. The anger is real; the fix does nothing.
> 3. *"Fix the worst-rated sellers"* — raw rating targets small sellers with noisy averages.
>    Ranking by stars lost targets the ones whose failure actually reaches customers.

### E. Three-minute video
Timed script (~420 words): problem → approach → insight → recommendation. Written to the second.

### F. One LinkedIn post
At the end, linking the live dashboard. Lead with the 47% result.

---

## The recommendation stack

| # | Recommendation | Evidence | Expected effect | Confidence |
|---|---|---|---|---|
| 1 | **Promise per order, not per platform** (risk-based ETA) | held-out test, 25,352 orders | −47% late orders at equal promise length | High |
| 2 | **Fix the multi-parcel completion bug** — don't mark an order delivered, or fire the survey, until the last parcel lands | OR 4.99; 36% vs 6% 1-star on-time; text 3.97× | ~342 excess 1-stars/yr, cheap fix | High |
| 3 | **Route pre-delivery 1-stars to live recovery** — 8,446 customers report non-receipt while still recoverable | 53% "não recebi" vs 16% | Recovery, not score inflation (RD says score won't move) | Medium |
| 4 | **Seller SLA on handoff time** — worst decile hands off 3.0d vs best 1.1d | scorecard, r = −0.37 | 20 sellers = 39% of stars lost | High |
| 5 | **Treat non-delivery as inventory, not logistics** — `unavailable`/`processing` score 1.3–1.5★ | 2,963 orders, 70.5% 1-star | 2,089 1-stars unreachable by delivery fixes | High |
| 6 | **Regional fulfilment for the North/Northeast** | distance r = +0.87 with delivery time | Structural; long horizon | Medium |

**The honest caveat that must appear in the report:** delivery failure explains 48.8% of 1-star
reviews. **51.2% arrived on time and the customer was furious anyway.** The promise problem is the
biggest single lever, not the whole story.
