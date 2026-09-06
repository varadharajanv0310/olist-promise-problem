"""
THE SELLER SCORECARD  -  ranking sellers by damage done, not by rating.

A raw seller rating is unfair and unactionable in both directions. A seller shipping heavy furniture
from Sao Paulo to Para is set up to score badly; a seller shipping books across town is set up to
score well. And a 2.1-star seller with nine orders is a rounding error next to a 3.9-star seller with
nine hundred.

So each seller is measured against what their OWN MIX predicts - the platform's average outcome for
the same categories and the same shipping distances - and then ranked by total stars lost, which is
volume times the shortfall. That produces an intervention list ordered by how much fixing each
seller is actually worth.
"""
import pandas as pd, numpy as np, pathlib, sys, warnings
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _style as S

warnings.filterwarnings("ignore")
S.apply()
ROOT = pathlib.Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
FIG, OUT = ROOT / "figures", ROOT / "data" / "processed"


def hdr(t): print("\n" + "=" * 92 + "\n" + t + "\n" + "=" * 92)


d = df[df.review_score.notna() & df.primary_seller_id.notna() & df.primary_category.notna()].copy()
d["dband"] = pd.cut(d.seller_customer_km, [-1, 100, 300, 600, 1200, 2500, 1e9],
                    labels=["<100", "100-300", "300-600", "600-1200", "1200-2500", "2500+"])

# ═══════════════════════════════════════════════════════ the benchmark
# expected outcome for an order = platform average for its (category, distance band) cell
cell = d.groupby(["primary_category", "dband"], observed=True).agg(
    cell_n=("review_score", "size"), cell_score=("review_score", "mean"),
    cell_1star=("is_one_star", "mean"), cell_late=("is_late", "mean"))
cell = cell[cell.cell_n >= 30]
d = d.join(cell, on=["primary_category", "dband"])
d = d.dropna(subset=["cell_score"])

MIN_ORDERS = 20
s = d.groupby("primary_seller_id").agg(
    orders=("order_id", "size"),
    revenue=("order_value", "sum"),
    score=("review_score", "mean"),
    exp_score=("cell_score", "mean"),
    pct_1star=("is_one_star", lambda x: np.nanmean(x) * 100),
    exp_1star=("cell_1star", lambda x: np.nanmean(x) * 100),
    late=("is_late", lambda x: np.nanmean(x) * 100),
    exp_late=("cell_late", lambda x: np.nanmean(x) * 100),
    handoff=("t_handoff", "median"),
    med_km=("seller_customer_km", "median"),
    state=("seller_state", "first"),
    top_cat=("primary_category", lambda x: x.mode().iloc[0] if len(x.mode()) else None),
)
s = s[s.orders >= MIN_ORDERS].copy()
s["score_gap"] = s.score - s.exp_score            # negative = worse than their mix predicts
s["late_gap"] = s.late - s.exp_late
s["stars_lost"] = -s.score_gap * s.orders          # positive = total damage

hdr(f"SELLER SCORECARD  ({len(s):,} sellers with >= {MIN_ORDERS} reviewed orders)")
print(f"  they cover {s.orders.sum():,} orders ({s.orders.sum() / len(d) * 100:.1f}% of reviewed volume) "
      f"and R${s.revenue.sum() / 1e6:.1f}M revenue")
print(f"\n  raw score spread      : p10 {s.score.quantile(.1):.2f}  median {s.score.median():.2f}  "
      f"p90 {s.score.quantile(.9):.2f}")
print(f"  MIX-ADJUSTED gap      : p10 {s.score_gap.quantile(.1):+.2f}  median {s.score_gap.median():+.2f}  "
      f"p90 {s.score_gap.quantile(.9):+.2f}")
print(f"  => the spread is {s.score_gap.quantile(.9) - s.score_gap.quantile(.1):.2f} stars wide even after")
print("     controlling for what they sell and how far they ship. Sellers genuinely differ.")

hdr("THE INTERVENTION LIST - top 20 sellers by total stars lost")
worst = s.sort_values("stars_lost", ascending=False).head(20)
show = worst[["orders", "revenue", "score", "exp_score", "score_gap", "stars_lost",
              "late", "exp_late", "handoff", "med_km", "state", "top_cat"]].copy()
show.index = [i[:12] + "..." for i in show.index]
print(show.round(2).to_string())
print(f"\n  these 20 sellers are {len(worst) / len(s) * 100:.1f}% of scored sellers and "
      f"{worst.orders.sum() / s.orders.sum() * 100:.1f}% of orders,")
print(f"  but account for {worst.stars_lost.sum() / s[s.stars_lost > 0].stars_lost.sum() * 100:.1f}% "
      f"of all stars lost to seller underperformance.")
print(f"  combined revenue at risk: R${worst.revenue.sum() / 1e6:.2f}M")

hdr("WHAT SEPARATES A BAD SELLER FROM A GOOD ONE?")
s["tier"] = pd.qcut(s.score_gap, [0, .1, .5, .9, 1.0],
                    labels=["worst 10%", "below median", "above median", "best 10%"])
t = s.groupby("tier", observed=True).agg(
    sellers=("orders", "size"), orders=("orders", "sum"), score=("score", "mean"),
    score_gap=("score_gap", "mean"), late=("late", "mean"), exp_late=("exp_late", "mean"),
    late_gap=("late_gap", "mean"), handoff=("handoff", "median"), med_km=("med_km", "median"))
print(t.round(2).to_string())
print(f"\n  correlation across sellers: score_gap vs late_gap   r = {s.score_gap.corr(s.late_gap):+.3f}")
print(f"                              score_gap vs handoff    r = {s.score_gap.corr(s.handoff):+.3f}")
print(f"                              score_gap vs order size r = {s.score_gap.corr(np.log(s.orders)):+.3f}")
print("\n  => seller underperformance is mostly a FULFILMENT-SPEED problem they control:")
print("     the worst decile hands off to the carrier "
      f"{t.handoff.iloc[0] - t.handoff.iloc[-1]:+.2f} days slower than the best decile,")
print(f"     and runs {t.late_gap.iloc[0] - t.late_gap.iloc[-1]:+.1f}pp more late than its own mix predicts.")

hdr("CONCENTRATION - how much of the platform rides on how few sellers")
srt = s.sort_values("revenue", ascending=False)
cum = srt.revenue.cumsum() / srt.revenue.sum() * 100
for k in [10, 25, 50, 100]:
    print(f"  top {k:>3} sellers = {cum.iloc[k - 1]:5.1f}% of scored revenue   "
          f"(mean gap {srt.score_gap.iloc[:k].mean():+.3f} stars)")

# ── FIG ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10.2, 6.0))
ok = s.score_gap >= 0
ax.scatter(s.orders[ok], s.score_gap[ok], s=26, color=S.C1, alpha=0.45,
           edgecolor=S.SURFACE, linewidth=0.8, zorder=3, label="Meeting or beating their benchmark")
ax.scatter(s.orders[~ok], s.score_gap[~ok], s=26, color=S.CRITICAL, alpha=0.45,
           edgecolor=S.SURFACE, linewidth=0.8, zorder=3, label="Underperforming their benchmark")
w20 = worst.head(20)
ax.scatter(w20.orders, w20.score_gap, s=90, facecolor="none", edgecolor=S.CRITICAL,
           linewidth=1.8, zorder=4)
ax.axhline(0, color=S.MUTED, linewidth=1.2, zorder=2)
ax.set_xscale("log")
ax.set_xlabel("Orders (log scale)")
ax.set_ylabel("Stars above / below what their mix predicts")
ax.annotate("circled: the 20-seller\nintervention list", (w20.orders.iloc[0], w20.score_gap.iloc[0]),
            xytext=(18, -26), textcoords="offset points", fontsize=9, color=S.CRITICAL,
            fontweight="600", arrowprops=dict(arrowstyle="->", color=S.CRITICAL, lw=1.2))
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.005), ncol=2)
ax.set_title("Same categories, same distances, very different sellers", loc="left", pad=42)
ax.text(0, 1.075, f"{len(s):,} sellers with {MIN_ORDERS}+ reviewed orders, benchmarked against the "
                  "platform average for their own category and distance mix",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "Ranking by raw rating would target small sellers with noisy averages. Ranking by stars "
            "lost targets the ones whose underperformance actually reaches customers.")
S.save(fig, "q8_seller_scorecard", FIG)

s.sort_values("stars_lost", ascending=False).to_parquet(OUT / "seller_scorecard.parquet")
print(f"\n  -> {OUT / 'seller_scorecard.parquet'}  ({len(s):,} sellers)")
