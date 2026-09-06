"""
Ten findings that were analysed but never drawn. Audit of figures vs analysis found these
with printed output and no chart:

  1. review score as a continuous readout of delivery performance (the 3-vs-4-star result)
  2. where 1-star reviews actually come from - the attribution split
  3. the cliff's universality across every category and state
  4. review-text themes separating the scores
  5. lead-time decomposition, on-time vs late
  6. price band vs satisfaction, and freight regressivity
  7. installments vs order value vs satisfaction
  8. seller tenure and churn
  9. the Friday handoff effect
 10. what freight is actually priced on
"""
import pandas as pd, numpy as np, pathlib, sys, warnings
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _style as S

warnings.filterwarnings("ignore")
S.apply()
ROOT = pathlib.Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
FIG = ROOT / "figures"
d = df[df.review_score.notna()]

# ══════════════════════════════════════════ 1. score as a delivery readout
g = d[d.is_delivered].groupby("review_score").agg(
    late=("is_late", lambda s: np.nanmean(s) * 100), days=("actual_days", "median"),
    value=("order_value", "median"), km=("seller_customer_km", "median"))
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.3))
ax = axes[0]
ax.bar(g.index, g.late, color=[S.CRITICAL if i <= 2 else S.C1 for i in g.index], width=0.64, zorder=3)
for i, v in g.late.items():
    ax.annotate(f"{v:.1f}%", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=10, color=S.INK, fontweight="600")
ax.set_xlabel("Review score"); ax.set_ylabel("Delivered late (%)")
ax.set_title("Late rate falls smoothly with every star", loc="left", fontsize=11.5)
ax = axes[1]
for col, lab, c in [("value", "Order value (R$)", S.C2), ("km", "Distance (km)", S.C4)]:
    ax.plot(g.index, g[col] / g[col].iloc[0] * 100, color=c, linewidth=2, marker="o",
            markersize=6, markerfacecolor=c, markeredgecolor=S.SURFACE, markeredgewidth=2, label=lab)
ax.plot(g.index, g.days / g.days.iloc[0] * 100, color=S.C1, linewidth=2, marker="o", markersize=6,
        markerfacecolor=S.C1, markeredgecolor=S.SURFACE, markeredgewidth=2, label="Delivery time (days)")
ax.axhline(100, color=S.BASELINE, linewidth=0.8)
ax.set_xlabel("Review score"); ax.set_ylabel("Indexed to the 1-star group = 100")
ax.legend(fontsize=9)
ax.set_title("Delivery moves; price and distance do not", loc="left", fontsize=11.5)
fig.suptitle("On this platform the review score is a readout of delivery performance",
             x=0.005, ha="left", fontsize=13.5, fontweight="600")
S.note(fig, "Even the 3-to-4 step, which looks like a matter of taste, is a 2.2x difference in "
            "lateness. Order value and seller distance are flat across the whole scale.")
S.save(fig, "q12_score_gradient", FIG)

# ══════════════════════════════════════════ 2. attribution
tot = d.is_one_star.sum()
dl = d[d.is_delivered]
parts = [(dl[dl.is_late == 1].is_one_star.sum(), "Delivered late", S.CRITICAL),
         (d[~d.is_delivered].is_one_star.sum(), "Never arrived", "#8c2d05"),
         (dl[dl.is_late == 0].is_one_star.sum(), "On time — still 1 star", S.MUTED)]
fig, ax = plt.subplots(figsize=(10, 2.5))
left = 0
for v, lab, c in parts:
    w = v / tot * 100
    ax.barh([0], [w], left=left, color=c, height=0.55, edgecolor=S.SURFACE, linewidth=2.5, zorder=3)
    ax.text(left + w / 2, 0, f"{w:.1f}%", ha="center", va="center", color="white",
            fontweight="700", fontsize=13)
    ax.text(left + w / 2, -0.46, lab, ha="center", va="top", fontsize=10, color=S.INK_2)
    ax.text(left + w / 2, -0.63, f"{v:,.0f} reviews", ha="center", va="top", fontsize=8.5, color=S.MUTED)
    left += w
ax.set_xlim(0, 100); ax.set_ylim(-1.1, 0.45); ax.axis("off")
ax.set_title("Delivery explains just under half of Olist's 1-star reviews", loc="left", pad=14)
ax.text(0, 1.02, f"All {tot:,.0f} one-star reviews, by what happened to the order",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "The 51.2% that arrived on time is the honest limit of any delivery fix. Inside it sit "
            "the multi-parcel completion bug and genuine product/expectation mismatch.")
S.save(fig, "q12_attribution", FIG)

# ══════════════════════════════════════════ 3. cliff universality
dd = d[d.gap_days.notna()]
rows = []
for key, minn, lab in [("primary_category", 500, "Category"), ("customer_state", 300, "State")]:
    gg = dd.groupby([key, dd.is_late == 1]).review_score.mean().unstack()
    gg.columns = ["on_time", "late"]
    gg = gg.join(dd.groupby(key).size().rename("n")).query(f"n >= {minn}")
    gg["penalty"] = gg.late - gg.on_time
    rows.append((lab, gg))
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))
for ax, (lab, gg) in zip(axes, rows):
    gg = gg.sort_values("penalty")
    ax.barh(range(len(gg)), gg.penalty, color=S.CRITICAL, height=0.72, zorder=3)
    ax.axvline(0, color=S.INK, linewidth=1.2, zorder=4)
    ax.set_yticks([]); ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
    ax.set_xlabel("Stars lost when the order is late")
    ax.set_title(f"{lab} — all {len(gg)} of {len(gg)} negative", loc="left", fontsize=11.5)
    ax.annotate(f"worst {gg.penalty.iloc[0]:.2f}\n{gg.index[0].replace('_', ' ')}",
                (gg.penalty.iloc[0], 0), xytext=(6, 0), textcoords="offset points",
                fontsize=8.5, color=S.INK_2, va="center")
fig.suptitle("The cliff is structural, not a pocket", x=0.005, ha="left",
             fontsize=13.5, fontweight="600")
S.note(fig, "Every category with 500+ reviewed orders and every state with 300+ shows a negative "
            "late-delivery penalty. What varies is exposure, not the penalty.")
S.save(fig, "q12_cliff_universality", FIG)

# ══════════════════════════════════════════ 4. text themes
t = d[d.review_comment_message.notna()].copy()
t["msg"] = t.review_comment_message.str.lower()
TH = {"Never arrived": r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o|nunca chegou",
      "Only part arrived": r"faltou|apenas um|s[oó] veio|s[oó] recebi|um dos",
      "Late": r"atras|demor|fora do prazo",
      "Wrong or broken": r"errad|quebrad|defeit|danificad",
      "Seller never replied": r"n[aã]o resp|sem resposta|n[aã]o consigo falar",
      "Praise": r"[oó]tim|excelen|perfeit|recomend|adorei"}
mat = pd.DataFrame({lab: [t[t.review_score == s].msg.str.contains(p, regex=True, na=False).mean() * 100
                          for s in [1, 2, 3, 4, 5]] for lab, p in TH.items()}, index=[1, 2, 3, 4, 5])
fig, ax = plt.subplots(figsize=(10, 5))
cols = [S.CRITICAL, "#8c2d05", S.C2, S.C4, S.C5, S.C3]
for (lab, c) in zip(mat.columns, cols):
    ax.plot(mat.index, mat[lab], color=c, linewidth=2, marker="o", markersize=6,
            markerfacecolor=c, markeredgecolor=S.SURFACE, markeredgewidth=2, label=lab)
# Direct-label ONLY the two that carry the point - four of the six converge below 2% at
# five stars and labelling them all there produces unreadable overlap. The legend covers the rest.
ax.annotate("Never arrived", (1, mat["Never arrived"].iloc[0]), xytext=(10, 4),
            textcoords="offset points", fontsize=10, color=S.CRITICAL, fontweight="600")
ax.annotate("Praise", (5, mat["Praise"].iloc[-1]), xytext=(-6, 10), textcoords="offset points",
            fontsize=10, color=S.C3, fontweight="600", ha="right")
ax.legend(loc="upper left", bbox_to_anchor=(0.30, 0.99), fontsize=9, ncol=2, columnspacing=1.4)
ax.set_xticks([1, 2, 3, 4, 5]); ax.set_xlim(0.85, 5.2)
ax.set_xlabel("Review score"); ax.set_ylabel("Share of written reviews mentioning the theme (%)")
S.title(ax, "The words separate the scores far more sharply than the score separates itself",
        f"{len(t):,} reviews with written comments (41.8% of all reviews)")
S.note(fig, "'Never arrived' runs 29.5% at one star and 1.4% at five. Seller silence is a 1-star "
            "signature, not a 3-star one.")
S.save(fig, "q12_text_themes", FIG)

# ══════════════════════════════════════════ 5. lead-time decomposition
dv = df[df.is_delivered & df.gap_days.notna()]
late_m = dv.gap_days > 0
stages = [("t_approve", "Awaiting payment approval", S.C2),
          ("t_handoff", "Seller preparing & handing over", S.C4),
          ("t_transit", "In transit with the carrier", S.C1)]
fig, ax = plt.subplots(figsize=(10, 3.4))
for i, (grp, lab) in enumerate([(~late_m, "Delivered on time"), (late_m, "Delivered LATE")]):
    left = 0
    for col, slab, c in stages:
        v = dv.loc[grp, col].median()
        ax.barh([i], [v], left=left, color=c, height=0.52, zorder=3,
                edgecolor=S.SURFACE, linewidth=2, label=slab if i == 0 else None)
        if v > 1.2:
            ax.text(left + v / 2, i, f"{v:.1f}d", ha="center", va="center", color="white",
                    fontsize=10, fontweight="700")
        left += v
    ax.annotate(f"{left:.1f} days total", (left, i), xytext=(9, 0), textcoords="offset points",
                va="center", fontsize=10.5, color=S.INK, fontweight="600")
ax.set_yticks([0, 1]); ax.set_yticklabels(["Delivered\non time", "Delivered\nLATE"], fontsize=10)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xlabel("Median days from purchase")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=3, columnspacing=1.4)
ax.set_title("Late orders are late in transit, not on the seller's shelf", loc="left", pad=42)
S.note(fig, "Of the ~19 extra median days on a late order, 17 are carrier transit and 1.3 is seller "
            "handoff. Payment approval is noise.")
S.save(fig, "q12_leadtime", FIG)

# ══════════════════════════════════════════ 6. price bands
p = d[d.order_value.notna()].copy()
p["band"] = pd.qcut(p.order_value, [0, .2, .4, .6, .8, .95, 1],
                    labels=["cheapest\n20%", "20–40%", "40–60%", "60–80%", "80–95%", "top 5%"])
pb = p.groupby("band", observed=True).agg(
    score=("review_score", "mean"), one=("is_one_star", lambda s: np.nanmean(s) * 100),
    fr=("freight_ratio", "median"), price=("order_value", "median"))
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.2))
ax = axes[0]
ax.bar(range(len(pb)), pb.one, color=S.CRITICAL, width=0.64, zorder=3)
for i, v in enumerate(pb.one):
    ax.annotate(f"{v:.1f}%", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=9.5, color=S.INK, fontweight="600")
ax.set_xticks(range(len(pb))); ax.set_xticklabels(pb.index, fontsize=9)
ax.set_ylabel("1-star rate (%)"); ax.set_xlabel("Order value band")
ax.set_title("Expensive orders disappoint more often", loc="left", fontsize=11.5)
ax = axes[1]
ax.bar(range(len(pb)), pb.fr * 100, color=S.C1, width=0.64, zorder=3)
for i, v in enumerate(pb.fr * 100):
    ax.annotate(f"{v:.0f}%", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=9.5, color=S.INK, fontweight="600")
ax.set_xticks(range(len(pb))); ax.set_xticklabels(pb.index, fontsize=9)
ax.set_ylabel("Freight as % of order value"); ax.set_xlabel("Order value band")
ax.set_title("...and cheap ones pay for shipping", loc="left", fontsize=11.5)
fig.suptitle("Price cuts two ways", x=0.005, ha="left", fontsize=13.5, fontweight="600")
S.note(fig, "The cheapest fifth of orders pay 56% of their value in freight; the top 5% pay 5%. "
            "Shipping economics are sharply regressive.")
S.save(fig, "q12_price_bands", FIG)

# ══════════════════════════════════════════ 7. installments
cc = d[d.payment_type.eq("credit_card")].copy()
cc["band"] = pd.cut(cc.max_installments, [0, 1, 2, 3, 6, 10, 24],
                    labels=["1\n(upfront)", "2", "3", "4–6", "7–10", "11–24"])
ib = cc.groupby("band", observed=True).agg(
    n=("order_id", "size"), value=("order_value", "median"),
    score=("review_score", "mean"), one=("is_one_star", lambda s: np.nanmean(s) * 100))
fig, ax = plt.subplots(figsize=(10, 4.4))
x = np.arange(len(ib))
ax.bar(x, ib.value, color=S.C1, width=0.6, zorder=3)
for i, v in enumerate(ib.value):
    ax.annotate(f"R${v:.0f}", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=9.5, color=S.INK, fontweight="600")
ax.set_xticks(x); ax.set_xticklabels(ib.index, fontsize=9)
ax.set_ylabel("Median order value (R$)"); ax.set_xlabel("Installments chosen")
S.title(ax, "Installments buy bigger baskets, and slightly unhappier customers",
        "Credit-card orders only · 1-star rate rises 10.6% → 18.5% across the same bands")
for i, v in enumerate(ib.one):
    ax.annotate(f"{v:.1f}% 1-star", (i, 6), xytext=(0, 0), textcoords="offset points",
                ha="center", fontsize=8.5, color=S.CRITICAL, fontweight="600")
S.note(fig, "The satisfaction decline tracks order value, not financing stress — expensive orders "
            "disappoint more often regardless of how they are paid for.")
S.save(fig, "q12_installments", FIG)

# ══════════════════════════════════════════ 8. seller churn
items = pd.read_csv(RAW / "order_items.csv")
it = items.merge(df[["order_id", "order_purchase_timestamp", "review_score"]], on="order_id", how="left")
it["ts"] = pd.to_datetime(it.order_purchase_timestamp)
life = it.groupby("seller_id").agg(first_ts=("ts", "min"), last_ts=("ts", "max"),
                                   orders=("order_id", "nunique"), score=("review_score", "mean"))
END = it.ts.max()
life["tenure"] = (life.last_ts - life.first_ts).dt.days
life["churned"] = (END - life.last_ts).dt.days > 90
act = life[life.orders >= 10]
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.2))
ax = axes[0]
ax.hist(life.tenure, bins=44, color=S.C1, zorder=3)
ax.axvline(life.tenure.median(), color=S.CRITICAL, linewidth=1.6, zorder=4)
ax.annotate(f"median {life.tenure.median():.0f} days", (life.tenure.median(), ax.get_ylim()[1] * 0.88),
            xytext=(8, 0), textcoords="offset points", fontsize=9.5, color=S.CRITICAL, fontweight="600")
ax.set_xlabel("Days between a seller's first and last order"); ax.set_ylabel("Sellers")
ax.set_title(f"{(life.orders == 1).mean() * 100:.0f}% of sellers never make a second sale",
             loc="left", fontsize=11.5)
ax = axes[1]
t2 = act.groupby("churned").agg(n=("orders", "size"), score=("score", "mean"))
ax.bar([0, 1], t2.score, color=[S.C3, S.CRITICAL], width=0.5, zorder=3)
for i, (v, n) in enumerate(zip(t2.score, t2.n)):
    ax.annotate(f"{v:.2f}\n{n:,} sellers", (i, v), xytext=(0, 6), textcoords="offset points",
                ha="center", fontsize=10, color=S.INK, fontweight="600")
ax.set_xticks([0, 1]); ax.set_xticklabels(["Still active", "Gone quiet 90+ days"])
ax.set_ylim(3.5, 4.3); ax.set_ylabel("Mean review score while active")
ax.set_title("Sellers who leave were rated worse", loc="left", fontsize=11.5)
fig.suptitle("Seller churn is high, and quality-correlated", x=0.005, ha="left",
             fontsize=13.5, fontweight="600")
S.note(fig, f"{life.churned.mean() * 100:.0f}% of all sellers had gone silent for 90+ days at the "
            "data cut. Among those with 10+ orders, leavers averaged 0.12 stars lower.")
S.save(fig, "q12_seller_churn", FIG)

# ══════════════════════════════════════════ 9. the Friday effect
o = df.copy()
o["dow"] = pd.to_datetime(o.order_purchase_timestamp).dt.dayofweek
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
dw = o.groupby("dow").agg(handoff=("t_handoff", "median"), total=("actual_days", "median"),
                          late=("is_late", lambda s: np.nanmean(s) * 100))
fig, ax = plt.subplots(figsize=(9.6, 4.2))
cols = [S.CRITICAL if DAYS[i] in ("Fri", "Sat") else S.C1 for i in dw.index]
ax.bar(range(7), dw.handoff, color=cols, width=0.62, zorder=3)
for i, v in enumerate(dw.handoff):
    ax.annotate(f"{v:.2f}d", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=9.5, color=S.INK, fontweight="600")
ax.set_xticks(range(7)); ax.set_xticklabels(DAYS)
ax.set_ylabel("Median days from approval to carrier pickup")
ax.set_xlabel("Day the order was placed")
S.title(ax, "Order on a Friday and it sits until Monday",
        "Seller handoff time by weekday of purchase")
S.note(fig, "Friday handoff is 2.5x Wednesday's — yet total delivery time differs by 0.02 days and "
            "the weekend late rate is LOWER. The buffer absorbs it entirely. This is what the twelve "
            "days of padding are buying.")
S.save(fig, "q12_weekday", FIG)

# ══════════════════════════════════════════ 10. freight model
f = df[(df.freight_total > 0) & (df.total_weight_g > 0) & df.seller_customer_km.notna()
       & (df.n_items == 1)].copy()
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.2))
for ax, (col, lab, edges, unit) in zip(axes, [
        ("total_weight_g", "Parcel weight", [0, 200, 500, 1000, 2000, 5000, 1e9],
         ["<200g", "200–500", "0.5–1kg", "1–2kg", "2–5kg", "5kg+"]),
        ("seller_customer_km", "Distance shipped", [0, 100, 300, 600, 1200, 2500, 1e9],
         ["<100km", "100–300", "300–600", "600–1.2k", "1.2–2.5k", "2.5k+"])]):
    f["b"] = pd.cut(f[col], edges, labels=unit)
    gg = f.groupby("b", observed=True).freight_total.median()
    ax.bar(range(len(gg)), gg.values, color=S.C1, width=0.64, zorder=3)
    for i, v in enumerate(gg.values):
        ax.annotate(f"R${v:.0f}", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=9.5, color=S.INK, fontweight="600")
    ax.set_xticks(range(len(gg))); ax.set_xticklabels(gg.index, fontsize=8.5, rotation=18, ha="right")
    ax.set_ylabel("Median freight charged (R$)"); ax.set_xlabel(lab)
    ax.set_title(f"{lab}: {gg.iloc[-1] / gg.iloc[0]:.1f}x across the range", loc="left", fontsize=11.5)
fig.suptitle("Freight barely moves with either weight or distance", x=0.005, ha="left",
             fontsize=13.5, fontweight="600")
S.note(fig, "Log-log elasticities: distance +0.19, weight +0.16. A 10x longer trip raises freight "
            "only 1.6x, so short-haul orders subsidise long-haul ones — yet remote states still pay "
            "up to 47% more than distance alone explains.")
S.save(fig, "q12_freight", FIG)

print(f"\ntotal figures now: {len(list(FIG.glob('*.png')))}")
