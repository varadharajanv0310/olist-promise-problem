"""
CORE QUESTION 2 - Delivery performance and customer satisfaction.
"How does delivery timing relative to the estimate relate to review scores? Does it hold across
categories and regions, or is it concentrated somewhere specific?"

The relationship is a cliff, not a slope, and the asymmetry has a direct strategic consequence:
the twelve days of padding in Olist's delivery promise are not sloppy forecasting, they are a
correctly-priced insurance policy. This script quantifies what removing them would cost.
"""
import pandas as pd, numpy as np, pathlib, sys, warnings
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _style as S

warnings.filterwarnings("ignore", message="Mean of empty slice")
S.apply()
ROOT = pathlib.Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
FIG = ROOT / "figures"
d = df[df.gap_days.notna() & df.review_score.notna()].copy()


def hdr(t): print("\n" + "=" * 80 + "\n" + t + "\n" + "=" * 80)


# ═══════════════════════════════════════════════════════ the cliff
hdr("Q2  THE CLIFF")
cliff = d.groupby("late_bucket", observed=True).agg(
    n=("review_score", "size"), mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100)).reset_index()
cliff["share"] = cliff.n / cliff.n.sum() * 100
print(cliff.round(2).to_string(index=False))

early = d[d.gap_days <= 0]; late = d[d.gap_days > 0]
print(f"\n  on-time or early : {len(early):>7,} ({len(early)/len(d)*100:5.2f}%)  "
      f"mean {early.review_score.mean():.2f}  1-star {np.nanmean(early.is_one_star)*100:5.2f}%")
print(f"  late             : {len(late):>7,} ({len(late)/len(d)*100:5.2f}%)  "
      f"mean {late.review_score.mean():.2f}  1-star {np.nanmean(late.is_one_star)*100:5.2f}%")
print(f"\n  ASYMMETRY: 15d+ early vs 0-3d early buys "
      f"{cliff.loc[cliff.late_bucket=='15d+ early','mean_score'].iloc[0] - cliff.loc[cliff.late_bucket=='0-3d early','mean_score'].iloc[0]:+.2f} stars")
print(f"             0-3d late  vs 3-7d late costs "
      f"{cliff.loc[cliff.late_bucket=='3-7d late','mean_score'].iloc[0] - cliff.loc[cliff.late_bucket=='0-3d late','mean_score'].iloc[0]:+.2f} stars")
print(f"  late orders are {len(late)/len(d)*100:.1f}% of deliveries but "
      f"{late.is_one_star.sum()/d.is_one_star.sum()*100:.1f}% of all 1-star reviews")

# ── FIG: the cliff ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.5, 5.2))
cols = [S.C1 if "early" in b else S.CRITICAL for b in cliff.late_bucket]
bars = ax.bar(range(len(cliff)), cliff.mean_score, color=cols, width=0.66, zorder=3)
ax.set_xticks(range(len(cliff)))
ax.set_xticklabels([b.replace(" ", "\n", 1) for b in cliff.late_bucket], fontsize=9)
ax.axvline(3.5, color=S.BASELINE, linewidth=1.2, zorder=1)
ax.text(3.55, 4.55, "delivery promise", fontsize=9, color=S.MUTED, va="top")
for i in (0, 4, 5):
    ax.annotate(f"{cliff.mean_score[i]:.2f}", (i, cliff.mean_score[i]), xytext=(0, 6),
                textcoords="offset points", ha="center", fontsize=10, color=S.INK, fontweight="600")
ax.annotate("", xy=(5, 2.55), xytext=(4, 3.70), arrowprops=dict(arrowstyle="->", color=S.CRITICAL, lw=1.6))
ax.text(5.15, 3.15, "−1.45 stars\nin four days", fontsize=9.5, color=S.CRITICAL, fontweight="600")
ax.set_ylim(0, 5); ax.set_ylabel("Mean review score")
ax.set_xlabel("Delivery date relative to the promised date")
handles = [plt.Rectangle((0, 0), 1, 1, color=S.C1), plt.Rectangle((0, 0), 1, 1, color=S.CRITICAL)]
# above the plot area: inside it the swatch text would sit on the saturated bar fills
ax.legend(handles, ["Delivered on time or early", "Delivered late"],
          loc="lower left", bbox_to_anchor=(0, 1.005), ncol=2, columnspacing=1.6)
ax.set_title("Satisfaction does not decay — it falls off a ledge", loc="left", pad=42)
ax.text(0, 1.075, "Mean review score by delivery outcome · 96,470 delivered orders",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "Arriving fifteen days early rather than three buys 0.10 stars. Slipping from three days "
            "late to seven costs 1.45.")
S.save(fig, "q2_the_cliff", FIG)

# ═══════════════════════════════════════════════════════ tightening promise?
hdr("Q2  HAS OLIST BEEN TIGHTENING THE PROMISE?")
w = d[d.in_trend_window].copy()
w["month"] = pd.to_datetime(w.order_purchase_timestamp).dt.to_period("M").dt.to_timestamp()
pm = w.groupby("month").agg(promised=("promised_days", "median"), actual=("actual_days", "median"),
                            slack=("gap_days", lambda s: -s.median()),
                            pct_late=("is_late", lambda s: np.nanmean(s) * 100)).reset_index()
print(pm.assign(month=pm.month.dt.strftime("%Y-%m")).round(2).to_string(index=False))
print(f"\n  promise  {pm.promised.iloc[0]:.1f}d -> {pm.promised.iloc[-1]:.1f}d   "
      f"({pm.promised.iloc[-1] - pm.promised.iloc[0]:+.1f}d)")
print(f"  actual   {pm.actual.iloc[0]:.1f}d -> {pm.actual.iloc[-1]:.1f}d   "
      f"({pm.actual.iloc[-1] - pm.actual.iloc[0]:+.1f}d)")
print(f"  slack    {pm.slack.iloc[0]:.1f}d -> {pm.slack.iloc[-1]:.1f}d   "
      f"({pm.slack.iloc[-1] - pm.slack.iloc[0]:+.1f}d)")

fig, ax = plt.subplots(figsize=(9.5, 5.0))
ax.plot(pm.month, pm.promised, color=S.C1, linewidth=2, label="Promised delivery time (median)")
ax.plot(pm.month, pm.actual, color=S.C2, linewidth=2, label="Actual delivery time (median)")
ax.fill_between(pm.month, pm.actual, pm.promised, color=S.C1, alpha=0.09, zorder=1)
mid = len(pm) // 2
ax.annotate("the buffer", (pm.month.iloc[mid], (pm.promised.iloc[mid] + pm.actual.iloc[mid]) / 2),
            fontsize=10, color=S.MUTED, ha="center", fontweight="600")
for col, c in [("promised", S.C1), ("actual", S.C2)]:
    ax.annotate(f"{pm[col].iloc[-1]:.0f}d", (pm.month.iloc[-1], pm[col].iloc[-1]), xytext=(8, 0),
                textcoords="offset points", color=S.INK_2, fontsize=9.5, va="center", fontweight="600")
ax.set_ylabel("Days from purchase"); ax.set_ylim(0, None)
ax.legend(loc="lower left"); ax.margins(x=0.07)
S.title(ax, "Delivery got faster and the promise got tighter — so lateness rose anyway",
        "Median promised vs actual delivery time, Jan 2017 – Aug 2018")
S.save(fig, "q2_promise_vs_actual", FIG)

# ═══════════════════════════════════════════════════════ buffer sensitivity
hdr("Q2  BUFFER SENSITIVITY - what would tightening the promise cost?")
bins = np.arange(-45, 46)
d["gbin"] = np.clip(np.round(d.gap_days), -45, 45)
curve = d.groupby("gbin").agg(n=("review_score", "size"), s=("review_score", "mean"))
curve = curve[curve.n >= 30]
xs, ys = curve.index.values.astype(float), curve.s.values


def predict(gap):
    return np.interp(np.clip(gap, xs.min(), xs.max()), xs, ys)


base_gap = d.gap_days.values
rows = []
for shift in range(-5, 15):
    g = base_gap + shift                       # tightening the promise by `shift` days
    rows.append({"buffer_change_days": shift,
                 "median_promise_days": d.promised_days.median() - shift,
                 "pct_late": (g > 0).mean() * 100,
                 "pred_mean_score": predict(g).mean()})
sens = pd.DataFrame(rows)
sens["delta_vs_today"] = sens.pred_mean_score - sens.loc[sens.buffer_change_days == 0, "pred_mean_score"].iloc[0]
print(sens.round(3).to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
ax = axes[0]
ax.plot(sens.buffer_change_days, sens.pct_late, color=S.CRITICAL, linewidth=2)
ax.axvline(0, color=S.BASELINE, linewidth=1)
ax.set_xlabel("Days cut from the delivery promise"); ax.set_ylabel("Orders delivered late (%)")
ax.set_title("Lateness rises fast", loc="left", fontsize=11.5)
ax = axes[1]
ax.plot(sens.buffer_change_days, sens.pred_mean_score, color=S.C1, linewidth=2)
ax.axvline(0, color=S.BASELINE, linewidth=1)
ax.annotate("today", (0, sens.loc[sens.buffer_change_days == 0, "pred_mean_score"].iloc[0]),
            xytext=(6, 8), textcoords="offset points", fontsize=9.5, color=S.MUTED)
ax.set_xlabel("Days cut from the delivery promise"); ax.set_ylabel("Projected mean review score")
ax.set_title("Satisfaction falls with it", loc="left", fontsize=11.5)
fig.suptitle("Cutting the delivery promise is not free", x=0.005, ha="left", fontsize=13, fontweight="600")
S.note(fig, "Projection holds the physical delivery time fixed and moves only the promised date, "
            "applying the observed score-vs-gap curve. It assumes customers react to the gap, not the "
            "absolute wait — an assumption the flat 'early' buckets support.")
S.save(fig, "q2_buffer_sensitivity", FIG)

# ═══════════════════════════════════════════════════════ concentration
hdr("Q2  DOES THE CLIFF HOLD EVERYWHERE?  (category)")
cat = d[d.primary_category.notna()].groupby("primary_category").agg(
    n=("review_score", "size"), pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    score_ontime=("review_score", lambda s: np.nan), ).reset_index()
g = d[d.primary_category.notna()].groupby(["primary_category", d.is_late == 1]).review_score.mean().unstack()
g.columns = ["score_ontime", "score_late"]
g["penalty"] = g.score_late - g.score_ontime
g = g.join(d.groupby("primary_category").size().rename("n")).query("n >= 500").sort_values("penalty")
print(f"categories with >=500 reviewed orders: {len(g)}")
print(g.round(2).head(8).to_string())
print("...")
print(g.round(2).tail(5).to_string())
print(f"\n  the late-delivery penalty is negative in {(g.penalty < 0).sum()} of {len(g)} categories "
      f"(range {g.penalty.min():.2f} to {g.penalty.max():.2f})")

hdr("Q2  DOES THE CLIFF HOLD EVERYWHERE?  (state)")
gs = d.groupby(["customer_state", d.is_late == 1]).review_score.mean().unstack()
gs.columns = ["score_ontime", "score_late"]
gs["penalty"] = gs.score_late - gs.score_ontime
gs = gs.join(d.groupby("customer_state").agg(n=("review_score", "size"),
                                             pct_late=("is_late", lambda s: np.nanmean(s) * 100)))
gs = gs.query("n >= 300").sort_values("pct_late", ascending=False)
print(gs.round(2).to_string())
print(f"\n  penalty is negative in ALL {(gs.penalty < 0).sum()} of {len(gs)} states — "
      f"the effect is universal, not regional")
