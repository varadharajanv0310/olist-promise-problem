"""
CORE QUESTION 4 - Product category performance.
"How do order volume, price and review scores differ across categories? Are any notably stronger or
weaker than the platform average?"

The raw score ranking is misleading, because categories do not ship the same way: heavy furniture
travels differently from a paperback. So every category is scored twice - as observed, and among
ON-TIME deliveries only. The difference separates a category with a product problem from a category
with a logistics problem, and those need different owners.
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


def hdr(t): print("\n" + "=" * 88 + "\n" + t + "\n" + "=" * 88)


d = df[df.primary_category.notna() & df.review_score.notna()].copy()
MIN_N = 300

# ═══════════════════════════════════════════════════════ category table
cat = d.groupby("primary_category").agg(
    orders=("order_id", "size"),
    revenue=("order_value", "sum"),
    avg_price=("order_value", "mean"),
    med_price=("order_value", "median"),
    mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    med_delivery=("actual_days", "median"),
    freight_ratio=("freight_ratio", "median"),
    med_km=("seller_customer_km", "median"),
)
# the control: score among on-time deliveries only
ontime = d[d.is_late == 0].groupby("primary_category").review_score.mean().rename("score_ontime")
cat = cat.join(ontime)
cat["rev_share"] = cat.revenue / cat.revenue.sum() * 100
big = cat[cat.orders >= MIN_N].copy()

PLAT_SCORE = d.review_score.mean()
PLAT_ONTIME = d[d.is_late == 0].review_score.mean()
PLAT_LATE = np.nanmean(d.is_late) * 100

hdr(f"Q4  CATEGORY SCOREBOARD  ({len(big)} categories with >= {MIN_N} reviewed orders, "
    f"{big.orders.sum():,} orders = {big.orders.sum() / len(d) * 100:.1f}% of volume)")
print(f"platform mean score {PLAT_SCORE:.3f} | on-time-only {PLAT_ONTIME:.3f} | late rate {PLAT_LATE:.2f}%\n")
show = big.sort_values("orders", ascending=False)[
    ["orders", "rev_share", "avg_price", "mean_score", "score_ontime", "pct_1star", "pct_late",
     "med_delivery", "freight_ratio", "med_km"]]
print(show.round(2).to_string())

# ═══════════════════════════════════════════════════════ strongest / weakest
hdr("Q4  STRONGEST AND WEAKEST vs THE PLATFORM")
big["vs_platform"] = big.mean_score - PLAT_SCORE
r = big.sort_values("vs_platform")
print("WEAKEST (raw mean score):")
print(r[["orders", "mean_score", "score_ontime", "pct_late", "avg_price"]].head(8).round(2).to_string())
print("\nSTRONGEST (raw mean score):")
print(r[["orders", "mean_score", "score_ontime", "pct_late", "avg_price"]].tail(8).round(2).to_string())

# ═══════════════════════════════════════════════════════ the decomposition
hdr("Q4  PRODUCT PROBLEM OR LOGISTICS PROBLEM?")
big["delivery_drag"] = big.mean_score - big.score_ontime      # how much lateness costs the category
big["product_gap"] = big.score_ontime - PLAT_ONTIME           # how it does when delivery is not the issue
dec = big.sort_values("product_gap")[
    ["orders", "mean_score", "score_ontime", "product_gap", "delivery_drag", "pct_late", "avg_price"]]
print("Categories that are WEAK EVEN WHEN DELIVERED ON TIME  (product / listing / expectation problem):")
print(dec.head(7).round(3).to_string())
print("\nCategories that are FINE ON TIME but dragged down by delivery (logistics problem):")
print(big.sort_values("delivery_drag").head(7)[
    ["orders", "mean_score", "score_ontime", "product_gap", "delivery_drag", "pct_late", "med_km"]]
      .round(3).to_string())
print(f"\n  correlation across categories:  late rate vs mean score   r = {big.pct_late.corr(big.mean_score):+.3f}")
print(f"                                  price     vs mean score   r = {big.avg_price.corr(big.mean_score):+.3f}")
print(f"                                  distance  vs mean score   r = {big.med_km.corr(big.mean_score):+.3f}")
print(f"                                  freight%  vs mean score   r = {big.freight_ratio.corr(big.mean_score):+.3f}")
print(f"\n  spread in on-time score across categories: "
      f"{big.score_ontime.min():.2f} ({big.score_ontime.idxmin()}) to "
      f"{big.score_ontime.max():.2f} ({big.score_ontime.idxmax()})")

# ── FIG 1: the portfolio ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10.5, 6.4))
sz = np.sqrt(big.revenue / 1000) * 5
above = big.mean_score >= PLAT_SCORE
ax.scatter(big.orders[above], big.mean_score[above], s=sz[above], color=S.C1, alpha=0.5,
           edgecolor=S.SURFACE, linewidth=2, zorder=3, label="At or above platform average")
ax.scatter(big.orders[~above], big.mean_score[~above], s=sz[~above], color=S.CRITICAL, alpha=0.5,
           edgecolor=S.SURFACE, linewidth=2, zorder=3, label="Below platform average")
ax.axhline(PLAT_SCORE, color=S.BASELINE, linewidth=1.1, zorder=1)
ax.text(big.orders.max() * 1.05, PLAT_SCORE, f"platform\n{PLAT_SCORE:.2f}", fontsize=8.5,
        color=S.MUTED, va="center")
ax.set_xscale("log")
LABEL = set(big.nlargest(6, "orders").index) | set(big.nsmallest(4, "mean_score").index) | \
        set(big.nlargest(3, "mean_score").index)
for c, row in big.iterrows():
    if c in LABEL:
        ax.annotate(c.replace("_", " "), (row.orders, row.mean_score), xytext=(0, 11),
                    textcoords="offset points", ha="center", fontsize=8.5, color=S.INK_2)
ax.set_xlabel("Orders (log scale)"); ax.set_ylabel("Mean review score")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.005), ncol=2)
ax.set_title("Volume does not buy satisfaction, and price does not either", loc="left", pad=42)
ax.text(0, 1.075, f"{len(big)} categories with {MIN_N}+ reviewed orders · bubble sized by revenue",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "The biggest categories sit near the platform mean by construction — the interesting "
            "cases are the small, low-scoring ones on the left.")
S.save(fig, "q4_category_portfolio", FIG)

# ── FIG 2: product vs logistics ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.8, 7.2))
plot = big.sort_values("product_gap")
y = np.arange(len(plot))
ax.hlines(y, plot.score_ontime, plot.mean_score, color=S.BASELINE, linewidth=1.6, zorder=2)
ax.scatter(plot.score_ontime, y, s=52, color=S.C1, zorder=3, edgecolor=S.SURFACE, linewidth=1.5,
           label="Score when delivered on time")
ax.scatter(plot.mean_score, y, s=52, color=S.CRITICAL, zorder=3, edgecolor=S.SURFACE, linewidth=1.5,
           label="Score as observed")
ax.axvline(PLAT_ONTIME, color=S.MUTED, linewidth=1, zorder=1)
ax.text(PLAT_ONTIME, len(plot) + 0.2, f"platform on-time {PLAT_ONTIME:.2f}", fontsize=8.5,
        color=S.MUTED, ha="center", va="bottom")
ax.set_yticks(y); ax.set_yticklabels([c.replace("_", " ") for c in plot.index], fontsize=8.5)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xlabel("Mean review score")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2)
ax.set_title("Two different problems wearing the same low score", loc="left", pad=40)
ax.text(0, 1.052, "Gap between the two dots is what late delivery costs that category",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "A category low on BOTH dots has a product or expectation problem. A category with a wide "
            "gap has a logistics problem. They belong to different teams.")
S.save(fig, "q4_product_vs_logistics", FIG)

# ═══════════════════════════════════════════════════════ price
hdr("Q4  DOES PRICE RELATE TO SATISFACTION?  (order level, not category level)")
d["price_band"] = pd.qcut(d.order_value, [0, .2, .4, .6, .8, .95, 1],
                          labels=["cheapest 20%", "20-40%", "40-60%", "60-80%", "80-95%", "top 5%"])
pb = d.groupby("price_band", observed=True).agg(
    n=("order_id", "size"), med_price=("order_value", "median"), mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    freight_ratio=("freight_ratio", "median"))
print(pb.round(2).to_string())
print(f"\n  cheapest 20% pay {pb.freight_ratio.iloc[0] * 100:.0f}% of order value in freight; "
      f"top 5% pay {pb.freight_ratio.iloc[-1] * 100:.0f}%")
