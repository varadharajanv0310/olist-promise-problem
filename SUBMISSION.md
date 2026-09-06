# Submission checklist — Olist Hackathon (Gradient Learning)

**Project:** The Promise Problem
**Repo:** https://github.com/varadharajanv0310/olist-promise-problem

---

## What goes where

| # | Deliverable | Status | What to submit |
|---|---|---|---|
| 1 | **Google Colab notebook** | ✅ built, verified | Upload `notebook/olist_promise_problem.ipynb` to Colab → **Share → Anyone with the link → Viewer** → submit that link |
| 2 | **Analysis report** | ✅ published | https://claude.ai/code/artifact/8fb42cc0-e0f0-4cfa-a478-b7ac857468c6 |
| 3 | **Three-minute video** | ⏳ **you record** | Script in `video/script.md`. Screen-record the dashboard, upload unlisted to YouTube/Drive, submit the link |
| 4 | **LinkedIn post** | ⏳ **you post** | Copy in `linkedin/final-post.md`. Submit the post URL + a screenshot of likes/comments at the deadline |
| — | Interactive dashboard | ✅ published | https://claude.ai/code/artifact/875ea937-031e-4599-8b37-538f111444d0 — include it as a bonus link wherever the form allows |

Everything goes into the Google Form the organisers share.

---

## The three things only you can do

### 1 · Publish the notebook (5 min)
1. colab.research.google.com → **File → Upload notebook** → pick `notebook/olist_promise_problem.ipynb`
2. **Run all** once, end to end, so the reviewer sees outputs. It will prompt for the nine CSVs —
   upload them, or drop them in a Drive folder named `olist` and it finds them automatically.
3. **Share → General access → Anyone with the link → Viewer.** Copy the link.

> The notebook has been executed end to end locally: all 37 code cells run clean, and every headline
> number reproduces (RD +0.15/SE 0.19 · 47% fewer late · 31.0/17.7/51.2 attribution split). It has no
> `statsmodels` dependency, which is the thing that usually breaks these in Colab.

### 2 · Record the video (30 min including retakes)
Script is timed to **2:55**. Screen-record the dashboard full-screen, let the loader finish, and
follow the section cues. Don't read the numbers off the screen — say them and let the screen confirm.

### 3 · Post on LinkedIn
Post the copy, tag **Gradient Learning with the @ picker** (a plain-text mention doesn't register),
then drop the three links as your own first comment about an hour later.

---

## Pre-flight checks

- [ ] Colab link opens in an incognito window (i.e. sharing is actually public)
- [ ] Video is unlisted-but-viewable, not private
- [ ] LinkedIn tag on Gradient Learning is a real link, not plain text
- [ ] Engagement screenshot taken **at the deadline**, not when you post
- [ ] Both artifact links open for someone who isn't you (share menu → anyone with the link)
- [ ] GitHub repo is public

---

## What's in the repo

```
notebook/     the submission notebook — 66 cells, 37 code, runs top to bottom
report/       the analysis report (template + build script)
dashboard/    the interactive frontend (template + data + build script)
scripts/      22 scripts: extraction → cleaning → Q1-Q6 → models → charts
figures/      30 figures
reports/      17 text outputs, one per analysis stage
video/        the three-minute script
linkedin/     the post
```

Data is gitignored (CC BY-NC-SA, ~150 MB). `README.md` says how to regenerate everything.

---

## If a judge asks one question, it will be one of these

**"How do you know the 47% is real and not overfitting?"**
Time-based split — trained on 71,118 orders through April 2018, tested on 25,352 orders from
May–August that the model never saw. Seller-history features are built from the training window only,
so nothing leaks backward. Every feature is knowable at checkout.

**"Isn't 'don't change the ETA' a non-recommendation?"**
It isn't the recommendation. The recommendation is to change the ETA *per order* instead of
platform-wide. And "tighten it" isn't hypothetical — Olist ran it for 19 months and tripled their
late rate.

**"You said delivery is the problem, then said it's only half."**
Correct, and that's in the report deliberately. Delivery failure is 48.8% of one-star reviews — the
biggest single lever, not the whole story. The other 51.2% arrived on time. Claiming otherwise would
have been overselling.

**"What did you get wrong?"**
Three things, all documented. The survey-timing hypothesis was my headline and the regression
discontinuity killed it. I predicted seller handoff drove late deliveries; it's 87% carrier transit.
And I expected listing quality to explain the on-time one-star residual; the effect is under 0.1
stars. All three corrections are in the notebook and the report.
