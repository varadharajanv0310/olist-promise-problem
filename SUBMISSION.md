# Submission — Olist Hackathon (Gradient Learning)

**Project:** The Promise Problem · **Team:** F1

---

## Form fields — copy-paste

| Field | Value |
|---|---|
| **Team name** * | `F1` |
| **Other team members** | *(leave empty if solo)* |
| **Demo video URL** * | ⏳ **the one thing still needed** — record, upload Unlisted, paste link |
| **Project or repo link** | `https://github.com/varadharajanv0310/olist-promise-problem` |
| **Login details** | `Not required — everything is public.` |
| **Anything else we should know?** | see block below |

### "Anything else we should know?" — paste this

```
The Promise Problem — an analysis of 99,441 Olist marketplace orders (Sep 2016 – Oct 2018).

The demo video is chaptered. If you are short on time, the core argument is the first
three minutes; the recommendation and the result are at the "a promise per order" chapter.

Live links:
Interactive dashboard  https://varadharajanv0310.github.io/olist-promise-problem/
Analysis report        https://varadharajanv0310.github.io/olist-promise-problem/report/
Colab notebook         <PASTE COLAB LINK>
Code                   https://github.com/varadharajanv0310/olist-promise-problem
LinkedIn post          <PASTE POST URL>

Headline finding: satisfaction is flat across every early-delivery bucket and collapses
past the promised date — 15 days early instead of 3 is worth +0.10 stars, while 3 days
late to 7 costs -1.45 and triples the 1-star rate. Olist's 12-day padding is therefore
insurance, not poor forecasting, and tightening it has already been tried: the promise
fell from 39 days to 13 between 2017 and 2018 and the late rate tripled.

The recommendation is a per-order delivery promise rather than one flat buffer, which
delivers 47% fewer late deliveries at the same average promise length, measured on
25,352 held-out orders.

Stated plainly in the report: delivery failure explains 48.8% of 1-star reviews. The
other 51.2% arrived on time, so it is the biggest single lever rather than the whole
problem. Three recommendations that seemed obvious were tested and dropped, including
one killed by a regression discontinuity.

The notebook runs top to bottom without errors; all statistics are implemented in numpy
because statsmodels 0.14.4 fails against the scipy version Colab ships.
```

---

## What's left

### 1 · Record the video — the only blocker
Script: `video/script.md`. Screen-record the dashboard at 1080p+, hard-refresh first so the loader
plays. Upload **Unlisted** (not Private) to YouTube or Drive. That URL is the one required field.

### 2 · Publish the notebook
colab.research.google.com → Upload notebook → `notebook/olist_promise_problem.ipynb` → **Run all** →
**Share → Anyone with the link → Viewer.** Drop the link into the block above.

> Verified locally: 37/37 cells, 0 errors, 13 figures, every headline number reproduces.

### 3 · Submit, then screenshot LinkedIn engagement at the deadline

---

## Done

Analysis · notebook · report · dashboard · both deployed to GitHub Pages · repo public and
correctly attributed · LinkedIn posted.

## If a judge asks

**"How do you know the 47% is real?"** Time-based split — trained through April 2018, tested on
25,352 orders from May–August the model never saw. Seller-history features come from the training
window only. Every input is knowable at checkout.

**"You said delivery is the problem, then said it's half."** Correct, and that's deliberate. 48.8%
is the biggest single lever, not the whole story.

**"What did you get wrong?"** Three things, all documented: the survey-timing hypothesis died to a
regression discontinuity; I predicted seller handoff drove late deliveries and it's 87% carrier
transit; and I expected listing quality to explain the on-time 1-star residual — the effect is under
0.1 stars.
