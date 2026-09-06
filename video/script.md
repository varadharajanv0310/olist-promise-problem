# Three-minute video — script

**Format:** screen-recording of the dashboard while narrating. It's interactive and it carries the
argument better than slides would. Have the dashboard open full-screen before you hit record.

**Pace:** 437 words ≈ 2:55 at a natural presenting pace (~150 wpm). Don't rush the pauses marked `—`;
they're where the numbers land.

**Order is mandated by the brief:** business problem → approach → insight → recommendations.

---

### 0:00 – 0:25 · The business problem
> *On screen: the hero. Let the loader finish first.*

"Olist connects small Brazilian merchants to the big marketplaces. Someone buys, a seller ships,
and once it arrives the customer rates it one to five stars.

Leadership has two years of orders, payments, reviews and delivery timestamps — and no consolidated
view connecting them. They know satisfaction varies. Nobody can say what actually drives it.

That's the question I took: what is really shaping the customer experience here, and where's the
clearest opportunity to improve it."

### 0:25 – 0:50 · The analytical approach
> *On screen: scroll slowly through the stat strip toward section 01.*

"I reduced all nine tables to one row per order — ninety-nine thousand orders, sixty-five columns —
and made every cleaning decision once, documented.

Then I ran it as an investigation rather than a survey. Form a hypothesis, try to kill it, and only
keep what survives. That mattered, because my headline hypothesis didn't survive — and I'll come
back to that."

### 0:50 – 2:05 · The insights
> *On screen: the cliff chart. Pause on it.*

"Here's the finding everything hangs from.

Satisfaction doesn't decay as delivery slips — it holds flat, then falls off a ledge. Arriving
fifteen days early instead of three buys you a tenth of a star. Slipping from three days late to
seven costs you **one and a half stars** and triples the one-star rate. —

So Olist padding every delivery estimate by twelve days isn't bad forecasting. It's insurance
against a wildly asymmetric downside.

> *Scroll to section 02.*

And the obvious recommendation — *tighten your estimates* — has already been tried. Over nineteen
months Olist cut its promise from thirty-nine days to thirteen while actual delivery improved by
under four. The late rate tripled. This chart is the post-mortem.

> *Scroll to section 04.*

One more thing, because it keeps me honest: delivery explains **forty-nine percent** of one-star
reviews. Not all of them. Half of the worst reviews arrived on time and the customer was still
unhappy. That's a different problem with a different owner."

### 2:05 – 2:50 · The recommendation
> *On screen: section 03. Drag the slider slowly, land on 95.*

"So if you shouldn't shorten the promise and you shouldn't lengthen it — what do you do?

You stop making one promise for the whole platform.

Olist applies the same twelve-day buffer to a hundred-and-sixty-kilometre São Paulo order and a
twenty-four-hundred-kilometre order to Pará. Predict each order's delivery time instead, and promise
a chosen risk level.

> *Land the slider. Let the −47% sit on screen.*

Same twenty-one-day average promise. **Forty-seven percent fewer late deliveries.** Tested on
twenty-five thousand orders the model never saw.

The buffer isn't cut — it's moved off the orders that never needed it."

### 2:50 – 2:55 · Close
> *On screen: section 06, the seller queue.*

"And when you're ready to act, this is who to call first."

---

## Recording notes

- **Screen-record at 1080p minimum.** The mono type is small; anything less and the numbers blur.
- **Let the loader run.** It's four seconds and it sets the tone.
- **Two rehearsals, not ten.** Slightly unpolished and confident beats over-rehearsed.
- If you'd rather not do a live walkthrough, the fallback is the figures in `figures/` in this order:
  `q2_the_cliff` → `q2_promise_vs_actual` → `q12_attribution` → `q7_risk_scorer` → `q8_seller_scorecard`.
- **Do not read the numbers off the screen.** Say them, and let the screen confirm.
