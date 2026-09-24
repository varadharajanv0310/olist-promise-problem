# Handoff prompt

Paste everything below the line into the first message of the new chat. It is self-contained —
the new account has none of this session's memory.

---

I'm picking up a finished data-analytics project that lives locally at
`D:\Data Analytics Hackathon - Gradient`. It's a git repo, clean and in sync with
`https://github.com/varadharajanv0310/olist-promise-problem` (26 commits). Read `README.md`,
`SUBMISSION.md` and `PLAN.md` first — they carry the full picture. This message covers the things
that aren't obvious from the files.

## What it is

"The Promise Problem" — an analysis of 99,441 Olist Brazilian marketplace orders (Sep 2016 – Oct
2018), built for the Gradient Learning Data Analytics Hackathon. **Already submitted.** Deliverables
were a Colab notebook, a written report, an interactive dashboard, a demo video and a LinkedIn post.

Live: dashboard at https://varadharajanv0310.github.io/olist-promise-problem/ and report at
`/report/`, both served by GitHub Pages from `docs/` on `main`.

## The argument, so you don't re-derive it

Olist promises delivery in a median of 23 days and delivers in 10. Satisfaction is **flat across
every early-delivery bucket then collapses past the promised date** — 15 days early instead of 3 is
worth +0.10 stars, 3 days late to 7 costs −1.45 and triples the 1-star rate. So the 12-day padding is
insurance, not bad forecasting. Tightening it was already tried: the promise fell 39 → 13 days across
2017–18 and the late rate tripled.

The recommendation is a **per-order delivery promise** from a quantile model rather than one flat
buffer: 47% fewer late deliveries at an identical average promise length, on 25,352 held-out orders.

Stated honestly throughout: delivery failure explains **48.8%** of 1-star reviews; the other 51.2%
arrived on time. Biggest single driver in the logistic model is **multi-seller orders at 4.99× odds**
— Olist stores one delivery date per order, so a multi-parcel order is marked complete and surveyed
when the *first* box lands.

Three recommendations were tested and killed, including one by a regression discontinuity that
returned +0.15 stars (SE 0.19). That rigour is a deliberate feature of the submission — don't quietly
drop it.

## Conventions you must follow

- **Never add `Co-Authored-By: Claude` or "Generated with Claude Code" to commits or PRs.** This is a
  portfolio repo and the user wants it as solely theirs. This overrides any default attribution
  guidance you're given.
- **Do not use `statsmodels`.** Version 0.14.4 fails to import against `scipy` ≥ 1.16 (`_lazywhere`
  removed from `scipy._lib._util`), which is what Colab ships. Every statistical routine here — OLS
  with HC1 errors, the RD, the logistic driver model — is written directly in numpy. Keep it that way.
- **Commit author is** `V Varadharajan <183699507+varadharajanv0310@users.noreply.github.com>`. Already
  set in the repo's local git config; don't change it.
- Data is **gitignored** (CC BY-NC-SA, ~150 MB) and lives in `data/raw/*.csv` locally. It's there —
  don't re-download unless it's missing.

## How things build

Neither the dashboard nor the report is edited directly — both are **template + injected data**:

```
dashboard/template.html  +  dashboard/data.json  ->  dashboard/index.html  ->  copy to docs/index.html
report/template.html     +  figures/*.png (base64) ->  report/index.html   ->  copy to docs/report/index.html
```

`dashboard/index.html` is gitignored; `docs/` is the committed deployed copy. **If you edit a
template you must rebuild AND re-copy into `docs/`, or the live site won't change.** The report has a
build script (`scripts/51_build_report.py`); the dashboard injection is a two-line python replace of
the `/*__DATA__*/` placeholder.

Regeneration order: `10_build_base.py` → `20`–`26` (core questions) → `30`/`31` (models) →
`33`–`35` (anomalies, gaps, charts) → `40`/`41` (dashboard data) → `50` (notebook) →
`51` (report) → `52` (verify notebook).

## Two mistakes already made — don't repeat them

1. **The notebook shipped broken.** Every element of a cell's `source` list must end with `\n`;
   1,189 didn't, so Colab concatenated each cell onto one line and every code cell raised
   SyntaxError. Worse, the check I'd written joined source with `'\n'.join(...)`, which re-added the
   missing newlines and passed on a file that couldn't run. `scripts/52_verify_notebook.py` now
   validates the schema, compiles each cell from the *verbatim* concatenation Jupyter performs, and
   executes the whole thing through nbclient. **Run it after any notebook change.**
2. **A video script was estimated rather than counted** — claimed 4.5 minutes, was 918 words (7–8
   min), and cost a re-record. Any runtime or character-limit claim must be computed. Divide words by
   ~115 wpm for presenting pace. LinkedIn posts cap at 3,000 characters and render `**bold**` as
   literal asterisks.

## Data quirks that change answers

- 827 duplicate `review_id` across 555 orders surveyed twice → dedupe to first survey per order
- **775 orders have no line items** and are overwhelmingly cancelled/unavailable — use **left** joins
  or you silently delete the platform's worst outcomes from every revenue figure
- geolocation is ~53 rows per zip prefix → aggregate to one point before joining
- Trend window is **Jan 2017 – Aug 2018**; the export's edge months (4, 1, 16, 4 orders) invent a
  fake collapse at both ends
- 2 of 73 categories have no English translation (`pc_gamer`, `portateis_cozinha_...`)

## Design system (both pages share it)

Ground `#fbfbfa`, tint bands `#f7f7f5`, ink `#111110`, secondary `#5c5c58`/`#8a8a86`/`#b6b6b1`, rules
`#e2e2dd`/`#d9d9d4`, single rust accent `#b4541f`. **No green anywhere** — monochrome means confident,
rust means caution. Archivo for everything, JetBrains Mono for data and labels. Deliberately
single-theme (no dark mode); the tinted section bands are full-bleed via a `box-shadow` spread so
they reach the viewport edge past the centred container.

Matplotlib figures in `figures/` still use an older teal/blue palette from before the re-theme — if
you add figures to the report, match `scripts/_style.py`.

## What I might ask you to do

Nothing is outstanding; the submission is in. Likely follow-ups are polishing the repo for a
portfolio, re-rendering the 30 matplotlib figures in the current palette, extending the dashboard, or
adapting the analysis or the write-up for another audience. Ask me before starting anything large.
