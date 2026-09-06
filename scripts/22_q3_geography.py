"""
CORE QUESTION 3 - Seller and geographic patterns.
"Sellers and customers are not evenly distributed across Brazil. How does that relate to delivery
performance, freight cost, or customer satisfaction?"

Q2 established that the late-delivery penalty is universal - every category, every state. So the
geography question is not "where are customers angrier", it is "where are customers more EXPOSED".
The answer is distance from the Sao Paulo seller cluster, and state is mostly a proxy for it.
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


def hdr(t): print("\n" + "=" * 80 + "\n" + t + "\n" + "=" * 80)


# ═══════════════════════════════════════════════════════ concentration
hdr("Q3  THE IMBALANCE - where sellers are vs where customers are")
cs = df.customer_state.value_counts(normalize=True) * 100
ss = df.dropna(subset=["seller_state"]).seller_state.value_counts(normalize=True) * 100
conc = pd.DataFrame({"customer_share": cs, "seller_share": ss}).fillna(0)
conc["imbalance"] = conc.seller_share - conc.customer_share
conc = conc.sort_values("customer_share", ascending=False)
print(conc.head(12).round(2).to_string())
print(f"\n  top 1 seller state (SP) supplies {ss.iloc[0]:.1f}% of orders but holds "
      f"{cs.get('SP', 0):.1f}% of customers")
print(f"  top 3 seller states supply {ss.head(3).sum():.1f}% of all orders")
print(f"  {(ss < 1).sum()} of {len(ss)} states supply under 1% of orders each")

fig, ax = plt.subplots(figsize=(9.5, 5.4))
top = conc.head(12).iloc[::-1]
y = np.arange(len(top))
ax.barh(y - 0.2, top.customer_share, height=0.38, color=S.C1, label="Share of customers", zorder=3)
ax.barh(y + 0.2, top.seller_share, height=0.38, color=S.C2, label="Share of sellers", zorder=3)
ax.set_yticks(y); ax.set_yticklabels(top.index)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xlabel("Share of marketplace (%)")
ax.annotate(f"{top.seller_share.iloc[-1]:.0f}%", (top.seller_share.iloc[-1], len(top) - 1 + 0.2),
            xytext=(6, 0), textcoords="offset points", va="center", fontsize=10,
            color=S.INK, fontweight="600")
ax.legend(loc="lower right")
S.title(ax, "Sao Paulo sells to Brazil; Brazil does not sell to Sao Paulo",
        "Share of customers vs share of fulfilling sellers, by state")
S.note(fig, "Every order shipped from SP to the north or northeast crosses most of a continent.")
S.save(fig, "q3_seller_customer_imbalance", FIG)

# ═══════════════════════════════════════════════════════ distance
hdr("Q3  DISTANCE IS THE MECHANISM")
d = df[df.seller_customer_km.notna() & df.gap_days.notna()].copy()
EDGES = [0, 50, 150, 300, 600, 1000, 1500, 2000, 1e9]
LABS = ["<50", "50-150", "150-300", "300-600", "600-1k", "1k-1.5k", "1.5k-2k", "2k+"]
d["dbin"] = pd.cut(d.seller_customer_km, EDGES, labels=LABS)
db = d.groupby("dbin", observed=True).agg(
    n=("order_id", "size"),
    med_delivery=("actual_days", "median"),
    med_transit=("t_transit", "median"),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    mean_freight=("freight_total", "mean"),
    mean_value=("order_value", "mean"),
).reset_index()
db["freight_pct_of_value"] = db.mean_freight / db.mean_value * 100
print(db.round(2).to_string(index=False))
print(f"\n  <50km  -> 2000km+ :  delivery {db.med_delivery.iloc[0]:.1f}d -> {db.med_delivery.iloc[-1]:.1f}d"
      f"   late {db.pct_late.iloc[0]:.1f}% -> {db.pct_late.iloc[-1]:.1f}%"
      f"   score {db.mean_score.iloc[0]:.2f} -> {db.mean_score.iloc[-1]:.2f}")
print(f"  freight rises {db.mean_freight.iloc[-1] / db.mean_freight.iloc[0]:.1f}x while order value "
      f"rises only {db.mean_value.iloc[-1] / db.mean_value.iloc[0]:.1f}x")

fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.3))
for ax, (col, lab, c, fmt) in zip(axes, [
        ("med_delivery", "Median delivery time (days)", S.C1, "{:.0f}d"),
        ("pct_late", "Delivered late (%)", S.CRITICAL, "{:.0f}%"),
        ("mean_score", "Mean review score", S.C3, "{:.2f}")]):
    ax.plot(range(len(db)), db[col], color=c, linewidth=2, marker="o", markersize=6,
            markerfacecolor=c, markeredgecolor=S.SURFACE, markeredgewidth=2)
    ax.set_xticks(range(len(db))); ax.set_xticklabels(db.dbin, rotation=45, ha="right", fontsize=8.5)
    ax.set_title(lab, loc="left", fontsize=11)
    for i in (0, len(db) - 1):
        ax.annotate(fmt.format(db[col].iloc[i]), (i, db[col].iloc[i]), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=9.5, color=S.INK, fontweight="600")
    ax.margins(x=0.12, y=0.22)
axes[1].set_xlabel("Distance from seller to customer (km)")
fig.suptitle("Distance sets delivery time, lateness and satisfaction together",
             x=0.005, ha="left", fontsize=13, fontweight="600")
S.note(fig, "98,176 orders with a resolvable seller and customer location. Distance is the great-circle "
            "distance between zip-code-prefix centroids.")
S.save(fig, "q3_distance_gradient", FIG)

# ═══════════════════════════════════════════════════════ state vs distance
hdr("Q3  IS IT THE STATE, OR IS IT THE DISTANCE?")
st = d.groupby("customer_state").agg(
    n=("order_id", "size"), med_km=("seller_customer_km", "median"),
    med_delivery=("actual_days", "median"), pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    mean_score=("review_score", "mean"), mean_freight=("freight_total", "mean"),
    mean_value=("order_value", "mean")).query("n >= 300")
st["freight_pct"] = st.mean_freight / st.mean_value * 100
st = st.sort_values("med_km", ascending=False)
print(st.round(2).to_string())
r_late = st.med_km.corr(st.pct_late)
r_score = st.med_km.corr(st.mean_score)
r_deliv = st.med_km.corr(st.med_delivery)
r_freight = st.med_km.corr(st.freight_pct)
print(f"\n  across states, median distance correlates with:")
print(f"    delivery time     r = {r_deliv:+.3f}")
print(f"    late rate         r = {r_late:+.3f}")
print(f"    mean review score r = {r_score:+.3f}")
print(f"    freight as % of order value r = {r_freight:+.3f}")

fig, ax = plt.subplots(figsize=(9.5, 5.6))
sizes = np.sqrt(st.n) * 3.2
ax.scatter(st.med_km, st.pct_late, s=sizes, color=S.C1, alpha=0.55,
           edgecolor=S.SURFACE, linewidth=2, zorder=3)
b = np.polyfit(st.med_km, st.pct_late, 1)
xs = np.linspace(st.med_km.min(), st.med_km.max(), 50)
ax.plot(xs, np.polyval(b, xs), color=S.MUTED, linewidth=1.4, zorder=2)
for s_, row in st.iterrows():
    if s_ in {"SP", "RJ", "MG", "AL", "CE", "MA", "AM", "RR", "AP", "PR", "RS", "BA", "PA"}:
        ax.annotate(s_, (row.med_km, row.pct_late), xytext=(0, -3), textcoords="offset points",
                    ha="center", va="center", fontsize=8.5, color=S.INK, fontweight="600", zorder=4)
ax.set_xlabel("Median seller-to-customer distance (km)")
ax.set_ylabel("Orders delivered late (%)")
S.title(ax, f"Distance explains most of the geographic gap  (r = {r_late:+.2f})",
        "One bubble per state, sized by order volume · states with 300+ reviewed orders")
S.note(fig, "Sao Paulo is not better run than Alagoas - it is closer to the sellers.")
S.save(fig, "q3_state_distance_vs_late", FIG)

# ═══════════════════════════════════════════════════════ freight fairness
hdr("Q3  WHO PAYS FOR THE DISTANCE?")
print(db[["dbin", "mean_value", "mean_freight", "freight_pct_of_value"]].round(2).to_string(index=False))
print(f"\n  a customer 2000km+ away pays R${db.mean_freight.iloc[-1]:.2f} freight on an "
      f"R${db.mean_value.iloc[-1]:.2f} order ({db.freight_pct_of_value.iloc[-1]:.1f}%)")
print(f"  a customer <50km away pays R${db.mean_freight.iloc[0]:.2f} on an "
      f"R${db.mean_value.iloc[0]:.2f} order ({db.freight_pct_of_value.iloc[0]:.1f}%)")
print(f"\n  freight per 100km travelled: R${db.mean_freight.iloc[-1] / 25:.2f} at 2500km "
      f"vs R${db.mean_freight.iloc[0] / 0.25:.2f} at 25km -> long routes are heavily cross-subsidised")

# ═══════════════════════════════════════════════════════ seller spread
hdr("Q3  SELLER CONCENTRATION (setup for the seller scorecard)")
sel = df.dropna(subset=["primary_seller_id"]).groupby("primary_seller_id").agg(
    orders=("order_id", "size"), revenue=("order_value", "sum"), score=("review_score", "mean"))
sel = sel.sort_values("revenue", ascending=False)
cum = sel.revenue.cumsum() / sel.revenue.sum() * 100
for pct in [1, 5, 10, 20]:
    k = max(1, int(len(sel) * pct / 100))
    print(f"  top {pct:>2}% of sellers ({k:>4,} of {len(sel):,}) = {cum.iloc[k-1]:5.1f}% of revenue")
print(f"\n  sellers with >=20 orders: {(sel.orders >= 20).sum():,}")
q = sel[sel.orders >= 20].score
print(f"  their mean-score spread: p10 {q.quantile(.1):.2f}  median {q.median():.2f}  p90 {q.quantile(.9):.2f}")
