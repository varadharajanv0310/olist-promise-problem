# Day 1 — LinkedIn post

**Visual to attach:** `figures/q2_promise_vs_actual.png` (the buffer chart — it sets up the hook)
**Tag:** use LinkedIn's @ picker for **Gradient Learning** so it links, don't type it as plain text.

---

🚀 **Day 1 of the Data Analytics Hackathon** conducted by **@Gradient Learning**.

I'm working on **The Promise Problem** — an analysis of ~100,000 real orders from Olist, a Brazilian
marketplace that connects small merchants to the big platforms.

📊 **The problem:** Olist has two years of orders, payments, reviews and delivery timestamps, but
nobody has connected them. Leadership knows satisfaction varies. Nobody can say what actually drives it.

💡 **My approach:** treat it like an investigation, not a dashboard. Form a hypothesis, then try to
kill it. Anything that survives goes in the report.

🔍 **Today's finding — and it surprised me:**

Olist promises delivery in a median of **23 days** and actually delivers in **10**.

My first instinct was "their forecasting is broken." So I checked what happens when they miss.

Arriving 15 days early instead of 3 earns **+0.10 stars**.
Slipping from 3 days late to 7 costs **−1.45 stars** and triples the 1-star rate.

That padding isn't sloppy forecasting. It's a correctly-priced insurance policy against a wildly
asymmetric downside.

And here's the part I didn't expect: over 19 months Olist quietly cut that buffer from **28 days to
6** — while their late rate climbed from 3% to 10%. The experiment already ran. The data recorded
what it cost.

🛠️ **What I'm building — three layers off one pipeline:**

→ **An analytics solution:** a full cleaning pipeline and evidence for six core business questions.
→ **A dashboard** that puts the findings in front of an ops team instead of burying them in a notebook.
→ **A predictive model** built from the insight itself: if breaking the promise is what costs Olist
its ratings, then score every order's *risk of being late* at checkout — and set the promise per
order instead of padding all of them by twelve days.

That last one is the part I'm most interested in. The analysis says "don't cut the buffer." The model
turns that into "cut it where it's safe, widen it where it isn't."

**Today's biggest learning:** the obvious recommendation ("your delivery estimates are inaccurate,
tighten them") would have been confidently, expensively wrong. Checking the asymmetry before
recommending the fix changed the entire conclusion.

**Where have you seen a metric that looked broken until you understood what it was protecting against?**

#DataAnalytics #DataAnalyticsHackathon #DataScience #Analytics #BuildWithData #ProductSpace
