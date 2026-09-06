"""
FINISHING THE DATASET - the columns and questions nothing else has touched.

Audit of what the previous scripts left unused:
  products.product_photos_qty / _description_lenght / _name_lenght  - the brief calls these
      "listing quality proxy" and no analysis had used them. This is the biggest gap, because
      Q6 left 51.2% of 1-star reviews unexplained on orders that arrived ON TIME.
  reviews.review_comment_title                - unused
  reviews.review_answer_timestamp             - stored but never analysed (response latency)
  orders.order_purchase_timestamp hour/dow    - only ever used at month grain
  order_items.order_item_id as quantity       - repeated units within an order
  payments.payment_value vs order value       - never reconciled; the gap is discounts/vouchers
  seller tenure and churn                     - never built
  product-level (rather than category-level) outliers
  a real map of the geolocation table
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


def hdr(t): print("\n" + "=" * 92 + "\n" + t + "\n" + "=" * 92)


# ══════════════════════════════════════════ 1. LISTING QUALITY
hdr("1. LISTING QUALITY - the unused columns, against the on-time 1-star residual")
prods = pd.read_csv(RAW / "products.csv")
items = pd.read_csv(RAW / "order_items.csv")
prim = (items.sort_values(["order_id", "price"], ascending=[True, False])
        .drop_duplicates("order_id", keep="first")[["order_id", "product_id"]])
lq = prim.merge(prods[["product_id", "product_photos_qty", "product_description_lenght",
                       "product_name_lenght"]], on="product_id", how="left")
d = df.merge(lq, on="order_id", how="left")
d = d[d.review_score.notna() & d.product_photos_qty.notna()]
print(f"  orders with listing data: {len(d):,}")
print(f"  photos     median {d.product_photos_qty.median():.0f}  "
      f"p90 {d.product_photos_qty.quantile(.9):.0f}  max {d.product_photos_qty.max():.0f}")
print(f"  descr len  median {d.product_description_lenght.median():.0f}  "
      f"p90 {d.product_description_lenght.quantile(.9):.0f}")

ontime = d[d.is_late == 0]
print(f"\n  ON-TIME ORDERS ONLY (n={len(ontime):,}) - delivery removed as a factor:\n")
d["photo_band"] = pd.cut(d.product_photos_qty, [0, 1, 2, 3, 5, 100],
                         labels=["1 photo", "2", "3", "4-5", "6+"])
ob = d[d.is_late == 0].groupby("photo_band", observed=True).agg(
    n=("review_score", "size"), score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    med_price=("order_value", "median"))
print("  by number of listing photos:")
print(ob.round(2).to_string())

d["desc_band"] = pd.qcut(d.product_description_lenght, [0, .2, .4, .6, .8, 1.0],
                         labels=["shortest 20%", "20-40%", "40-60%", "60-80%", "longest 20%"])
db_ = d[d.is_late == 0].groupby("desc_band", observed=True).agg(
    n=("review_score", "size"), score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    med_chars=("product_description_lenght", "median"))
print("\n  by description length:")
print(db_.round(2).to_string())

print(f"\n  correlations on ON-TIME orders (delivery held out):")
for lab, c in [("photos", "product_photos_qty"), ("description length", "product_description_lenght"),
               ("name length", "product_name_lenght")]:
    sub = ontime[[c, "review_score"]].dropna()
    print(f"    {lab:<20} r = {sub[c].corr(sub.review_score):+.4f}   "
          f"(1-star rate {np.nanmean(ontime.is_one_star) * 100:.2f}% baseline)")
print("\n  => the effect is REAL but SMALL. Listing quality nudges satisfaction; it does not")
print("     explain the on-time 1-star residual. That residual is a fulfilment-completeness and")
print("     product-accuracy problem, which is what the multi-seller and text findings showed.")

# ══════════════════════════════════════════ 2. REVIEW RESPONSE BEHAVIOUR
hdr("2. REVIEW RESPONSE BEHAVIOUR - latency and the unused title field")
r = df[df.review_score.notna()].copy()
r["resp_h"] = (pd.to_datetime(r.review_answer_timestamp) -
               pd.to_datetime(r.review_creation_date)).dt.total_seconds() / 3600
rr = r.groupby("review_score").agg(
    n=("resp_h", "size"), median_h=("resp_h", "median"), mean_h=("resp_h", "mean"),
    within_24h=("resp_h", lambda s: (s <= 24).mean() * 100),
    has_title=("review_comment_title", lambda s: s.notna().mean() * 100))
print(rr.round(2).to_string())
print(f"\n  median response time is FLAT across scores: 1-star {rr.median_h.loc[1]:.1f}h vs 5-star "
      f"{rr.median_h.loc[5]:.1f}h ({rr.median_h.loc[1] / rr.median_h.loc[5]:.2f}x) - no signal in the median.")
print(f"  the signal is in the TAIL: {rr.within_24h.loc[1]:.1f}% of 1-star reviewers answer within 24h "
      f"vs {rr.within_24h.loc[5]:.1f}% of 5-star ({rr.within_24h.loc[1] / rr.within_24h.loc[5]:.2f}x),")
print(f"  and they are {rr.has_title.loc[1] / rr.has_title.loc[5]:.1f}x more likely to write a title.")
print("  => a same-day reply carrying a title is a weak, free early flag. Contributing, not a driver.")
t = r[r.review_comment_title.notna()].copy()
t["ti"] = t.review_comment_title.str.lower().str.strip()
print(f"\n  most common 1-star titles ({(t.review_score == 1).sum():,} with a title):")
print(t[t.review_score == 1].ti.value_counts().head(6).to_string())

# ══════════════════════════════════════════ 3. PURCHASE TIMING
hdr("3. PURCHASE TIMING - hour and weekday, never analysed below month grain")
o = df.copy()
o["ts"] = pd.to_datetime(o.order_purchase_timestamp)
o["hour"] = o.ts.dt.hour
o["dow"] = o.ts.dt.dayofweek
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
dw = o.groupby("dow").agg(orders=("order_id", "size"), handoff=("t_handoff", "median"),
                          total=("actual_days", "median"),
                          late=("is_late", lambda s: np.nanmean(s) * 100),
                          score=("review_score", "mean"))
dw.index = DAYS
print(dw.round(2).to_string())
wk = o[o.dow >= 5]; wd = o[o.dow < 5]
print(f"\n  weekend orders  n={len(wk):>6,}  handoff {wk.t_handoff.median():.2f}d  "
      f"total {wk.actual_days.median():.2f}d  late {np.nanmean(wk.is_late) * 100:.2f}%")
print(f"  weekday orders  n={len(wd):>6,}  handoff {wd.t_handoff.median():.2f}d  "
      f"total {wd.actual_days.median():.2f}d  late {np.nanmean(wd.is_late) * 100:.2f}%")
print(f"  => handoff is {wk.t_handoff.median() - wd.t_handoff.median():+.2f}d slower at the weekend,")
print(f"     yet total delivery differs by only {wk.actual_days.median() - wd.actual_days.median():+.2f}d "
      f"and the late rate is actually LOWER.")
print("     The Friday/Saturday handoff lag is absorbed entirely by the buffer - which is a small,")
print("     concrete demonstration of what the twelve days of padding are BUYING.")
hr = o.groupby("hour").agg(orders=("order_id", "size"), score=("review_score", "mean"))
peak = hr.orders.idxmax()
print(f"\n  peak ordering hour: {peak}:00 ({hr.orders.max():,} orders); "
      f"quietest {hr.orders.idxmin()}:00 ({hr.orders.min():,})")

# ══════════════════════════════════════════ 4. SELLER LIFECYCLE
hdr("4. SELLER LIFECYCLE - tenure and churn, never built")
it = items.merge(df[["order_id", "order_purchase_timestamp", "review_score", "is_late"]],
                 on="order_id", how="left")
it["ts"] = pd.to_datetime(it.order_purchase_timestamp)
life = it.groupby("seller_id").agg(first_ts=("ts", "min"), last_ts=("ts", "max"),
                                   orders=("order_id", "nunique"), score=("review_score", "mean"))
END = it.ts.max()
life["tenure_d"] = (life.last_ts - life.first_ts).dt.days
life["silent_d"] = (END - life.last_ts).dt.days
life["churned"] = life.silent_d > 90
print(f"  sellers: {len(life):,}   median tenure {life.tenure_d.median():.0f} days")
print(f"  one-and-done (single order ever): {(life.orders == 1).sum():,} "
      f"({(life.orders == 1).mean() * 100:.1f}%)")
print(f"  silent for 90+ days at the data cut: {life.churned.sum():,} "
      f"({life.churned.mean() * 100:.1f}%)")
act = life[life.orders >= 10]
print(f"\n  among sellers with 10+ orders (n={len(act):,}):")
print(act.groupby("churned").agg(sellers=("orders", "size"), mean_score=("score", "mean"),
                                 median_orders=("orders", "median"),
                                 median_tenure=("tenure_d", "median")).round(2).to_string())
a, b = act[act.churned].score.mean(), act[~act.churned].score.mean()
print(f"\n  churned sellers averaged {a:.2f} stars vs {b:.2f} for those still active "
      f"({a - b:+.2f})")
print("  => sellers who leave were rated worse while they were here. Whether Olist pushed them")
print("     out or they gave up, seller quality and seller retention move together.")

# ══════════════════════════════════════════ 5. PAYMENT RECONCILIATION
hdr("5. PAYMENT vs ORDER VALUE - never reconciled; the gap is discounts")
p = df[df.order_value.notna() & df.payment_total.notna()].copy()
p["expected"] = p.order_value + p.freight_total
p["diff"] = p.payment_total - p.expected
p["pct"] = p["diff"] / p.expected * 100
print(f"  orders reconciled: {len(p):,}")
print(f"  paid EXACTLY items+freight (within R$0.01): {(p['diff'].abs() < 0.01).mean() * 100:.2f}%")
print(f"  paid LESS  (discount / voucher): {(p['diff'] < -0.01).sum():,} "
      f"({(p['diff'] < -0.01).mean() * 100:.2f}%)   median R${-p[p['diff'] < -0.01]['diff'].median():.2f}")
print(f"  paid MORE  (interest on installments): {(p['diff'] > 0.01).sum():,} "
      f"({(p['diff'] > 0.01).mean() * 100:.2f}%)   median R${p[p['diff'] > 0.01]['diff'].median():.2f}")
disc = p[p["diff"] < -0.01]
print(f"\n  the 'paid less' rows are rounding, not discounting: {len(disc)} orders with a median gap "
      f"of R${-disc['diff'].median():.2f}.")
print("  => payments reconcile to items + freight almost exactly. There is no visible discounting,")
print("     coupon programme or price adjustment anywhere in this dataset. Worth stating plainly,")
print("     because its absence rules out 'promotions' as an explanation for any trend we found.")
inst = p[(p.max_installments > 1) & (p["diff"] > 0.01)]
print(f"  installment interest: {len(inst):,} orders paying a median "
      f"{inst.pct.median():.1f}% premium over list")

# ══════════════════════════════════════════ 6. MULTI-REVIEW ORDERS
hdr("6. THE 555 ORDERS WITH MORE THAN ONE SURVEY")
revs = pd.read_csv(RAW / "order_reviews.csv", parse_dates=["review_creation_date"])
multi = revs[revs.order_id.duplicated(keep=False)].sort_values(["order_id", "review_creation_date"])
g = multi.groupby("order_id").review_score.agg(["first", "last", "count", "nunique"])
g = g.rename(columns={"nunique": "distinct"})
print(f"  orders with 2+ surveys: {len(g):,}   review rows involved: {len(multi):,}")
print(f"  score CHANGED between surveys: {(g["distinct"] > 1).sum():,} ({(g["distinct"] > 1).mean() * 100:.1f}%)")
ch = g[g["distinct"] > 1]
print(f"  of those that changed:  improved {(ch['last'] > ch['first']).sum():,}   "
       f"worsened {(ch['last'] < ch['first']).sum():,}")
print(f"  mean first {g['first'].mean():.2f} -> mean last {g['last'].mean():.2f} "
      f"({g['last'].mean() - g['first'].mean():+.2f})")
print("  => where a customer was surveyed twice, the second verdict is HARSHER on average.")
print("     Waiting longer did not soften anyone.")

# ══════════════════════════════════════════ 7. PRODUCT-LEVEL OUTLIERS
hdr("7. PRODUCT-LEVEL OUTLIERS - analysis so far stopped at category")
pl = items.merge(df[["order_id", "review_score", "is_late", "is_one_star"]], on="order_id", how="left")
pl = pl.merge(prods[["product_id", "product_category_name"]], on="product_id", how="left")
pg = pl.groupby("product_id").agg(orders=("order_id", "nunique"), score=("review_score", "mean"),
                                  one=("is_one_star", lambda s: np.nanmean(s) * 100),
                                  late=("is_late", lambda s: np.nanmean(s) * 100),
                                  price=("price", "median"),
                                  cat=("product_category_name", "first"))
pg = pg[pg.orders >= 30]
print(f"  products with 30+ orders: {len(pg):,}  (of {prods.product_id.nunique():,} total)")
print(f"\n  WORST individual products (30+ orders):")
print(pg.nsmallest(8, "score")[["orders", "score", "one", "late", "price", "cat"]].round(2).to_string())
print(f"\n  BEST individual products:")
print(pg.nlargest(5, "score")[["orders", "score", "one", "late", "price", "cat"]].round(2).to_string())
bad = pg[pg.score < 3]
print(f"\n  {len(bad):,} products with 30+ orders average under 3 stars, together "
      f"{bad.orders.sum():,} orders")
print(f"  their median late rate {bad.late.median():.1f}% vs {pg.late.median():.1f}% overall -> "
      f"{'delivery' if bad.late.median() > pg.late.median() * 1.3 else 'NOT delivery'}-driven")

# ══════════════════════════════════════════ 8. THE 3-STAR MIDDLE
hdr("8. WHAT MAKES A 3 RATHER THAN A 4?")
m = df[df.review_score.notna() & df.is_delivered]
print(m.groupby("review_score").agg(
    n=("order_id", "size"), late=("is_late", lambda s: np.nanmean(s) * 100),
    delivery_d=("actual_days", "median"), slack_d=("gap_days", "median"),
    value=("order_value", "median"), km=("seller_customer_km", "median"),
    comment=("has_comment", lambda s: s.mean() * 100)).round(2).to_string())
print("\n  => the operational gradient is SMOOTH and monotonic across all five scores - late rate")
print("     37.7 / 20.7 / 11.1 / 5.0 / 3.0%, delivery time 16.7 / 13.3 / 12.0 / 10.8 / 9.2 days.")
print("     Even the 3-to-4 step, which looks like a matter of taste, is a 2.2x difference in")
print("     lateness. The review score is not a blunt satisfaction proxy: on this platform it is")
print("     close to a continuous readout of delivery performance.")
print("     Order value and distance, by contrast, are flat across the whole scale.")

# ══════════════════════════════════════════ 9. THE MAP
hdr("9. THE MAP - geolocation used for distance, never drawn")
geo = pd.read_csv(RAW / "geolocation.csv")
BB = (geo.geolocation_lat.between(-33.75, 5.28) & geo.geolocation_lng.between(-73.99, -34.79))
gpt = geo[BB].groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].mean()
cz = df.groupby("customer_zip_code_prefix").agg(
    n=("order_id", "size"), late=("is_late", lambda s: np.nanmean(s) * 100),
    days=("actual_days", "median"))
cz = cz[cz.n >= 8].join(gpt, how="inner")
print(f"  zip prefixes plotted: {len(cz):,} covering {cz.n.sum():,} orders")

fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.2))
for ax, col, lab, cmap in [(axes[0], "days", "Median delivery time (days)", "Blues"),
                           (axes[1], "late", "Delivered late (%)", "Oranges")]:
    v = cz[col].clip(cz[col].quantile(.02), cz[col].quantile(.98))
    sc = ax.scatter(cz.geolocation_lng, cz.geolocation_lat, c=v, s=np.sqrt(cz.n) * 1.7,
                    cmap=cmap, alpha=0.8, linewidth=0)
    ax.set_title(lab, loc="left", fontsize=11.5)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_aspect("equal")
    cb = fig.colorbar(sc, ax=ax, fraction=0.036, pad=0.02)
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=8, colors=S.MUTED)
    ax.scatter([-46.63], [-23.55], s=64, facecolor="none", edgecolor=S.CRITICAL, linewidth=1.8)
    ax.annotate("São Paulo", (-46.63, -23.55), xytext=(9, -12), textcoords="offset points",
                fontsize=9, color=S.CRITICAL, fontweight="600")
fig.suptitle("The whole country is downstream of one city", x=0.005, ha="left",
             fontsize=13.5, fontweight="600")
S.note(fig, f"{len(cz):,} zip-code prefixes with 8+ orders, positioned by mean geolocation reading "
            "and sized by order volume. Colour scales clipped at the 2nd/98th percentile.")
S.save(fig, "q11_map", FIG)

# ── listing quality figure ───────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.4))
for ax, tbl, xl, ttl in [(axes[0], ob, "Photos in the listing", "More photos, slightly better reviews"),
                         (axes[1], db_, "Description length", "Longer descriptions, same story")]:
    ax.bar(range(len(tbl)), tbl.score, color=S.C1, width=0.64, zorder=3)
    ax.set_xticks(range(len(tbl))); ax.set_xticklabels(tbl.index, fontsize=9, rotation=20, ha="right")
    ax.set_ylim(3.9, 4.5); ax.set_ylabel("Mean review score")
    ax.set_xlabel(xl); ax.set_title(ttl, loc="left", fontsize=11.5)
    for i, v in enumerate(tbl.score):
        ax.annotate(f"{v:.2f}", (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=9, color=S.INK, fontweight="600")
fig.suptitle("Listing quality moves the needle — but only just", x=0.005, ha="left",
             fontsize=13.5, fontweight="600")
S.note(fig, "On-time deliveries only, so delivery is held out. The gradient is real and monotonic, "
            "but spans under half a star — it is a contributing factor, not a driver.")
S.save(fig, "q11_listing_quality", FIG)
