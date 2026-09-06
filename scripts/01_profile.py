"""Profiling pass: structural integrity, quality, and first tests of the core hypotheses."""
import pandas as pd, numpy as np, pathlib
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 50)
R = pathlib.Path(r"D:\Data Analytics Hackathon - Gradient\data\raw")

def rd(n, **kw): return pd.read_csv(R / f"{n}.csv", **kw)
DATES_O = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
           "order_delivered_customer_date", "order_estimated_delivery_date"]

orders  = rd("orders", parse_dates=DATES_O)
items   = rd("order_items")
pays    = rd("order_payments")
revs    = rd("order_reviews", parse_dates=["review_creation_date", "review_answer_timestamp"])
cust    = rd("customers")
prods   = rd("products")
sellers = rd("sellers")
geo     = rd("geolocation")
trans   = rd("category_translation")

def hdr(t): print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)

hdr("1. STRUCTURAL INTEGRITY")
for name, df, key in [("orders", orders, "order_id"), ("customers", cust, "customer_id"),
                      ("products", prods, "product_id"), ("sellers", sellers, "seller_id"),
                      ("reviews", revs, "review_id")]:
    print(f"{name:<12} rows={len(df):>8,}  unique {key}={df[key].nunique():>8,}  "
          f"dup_keys={len(df) - df[key].nunique():>6,}")
print(f"\nreviews: unique order_id = {revs.order_id.nunique():,}  "
      f"(orders with >1 review = {(revs.groupby('order_id').size() > 1).sum():,})")
print(f"fully duplicated review rows = {revs.duplicated().sum():,}")
print(f"orders with items    = {items.order_id.nunique():,} / {len(orders):,}  "
      f"(missing = {len(orders) - items.order_id.nunique():,})")
print(f"orders with payments = {pays.order_id.nunique():,}")
print(f"orders with reviews  = {revs.order_id.nunique():,}")
print(f"multi-item orders    = {(items.groupby('order_id').size() > 1).sum():,}")
print(f"multi-seller orders  = {(items.groupby('order_id').seller_id.nunique() > 1).sum():,}")
print(f"multi-payment orders = {(pays.groupby('order_id').size() > 1).sum():,}")

hdr("2. MISSINGNESS (orders / products / reviews)")
for nm, df in [("orders", orders), ("products", prods), ("reviews", revs)]:
    m = df.isna().sum(); m = m[m > 0]
    print(f"\n-- {nm} --"); print(m.to_string() if len(m) else "  none")

hdr("3. ORDER STATUS")
st = orders.order_status.value_counts()
print(pd.DataFrame({"n": st, "pct": (st / len(orders) * 100).round(2)}).to_string())

hdr("4. TIME COVERAGE  (head/tail truncation check)")
orders["ym"] = orders.order_purchase_timestamp.dt.to_period("M")
mv = orders.groupby("ym").size()
print("first 8 months:"); print(mv.head(8).to_string())
print("\nlast 5 months:"); print(mv.tail(5).to_string())
print(f"\nfull range: {orders.order_purchase_timestamp.min()}  ->  {orders.order_purchase_timestamp.max()}")

hdr("5. REVIEW SCORE DISTRIBUTION (is the mean even the right metric?)")
sc = revs.review_score.value_counts().sort_index()
print(pd.DataFrame({"n": sc, "pct": (sc / len(revs) * 100).round(2)}).to_string())
print(f"\nmean={revs.review_score.mean():.3f}  median={revs.review_score.median():.0f}  "
      f"1-2 star rate={(revs.review_score <= 2).mean() * 100:.2f}%")
print(f"has comment message = {revs.review_comment_message.notna().mean() * 100:.1f}%")
print("\ncomment rate BY score (do angry people write more?):")
print(revs.groupby("review_score").review_comment_message
      .apply(lambda s: round(s.notna().mean() * 100, 1)).to_string())

hdr("6. DELIVERY: IS THE ETA PADDED?  (hypothesis A)")
d = orders[orders.order_status.eq("delivered") & orders.order_delivered_customer_date.notna()].copy()
d["actual_days"]   = (d.order_delivered_customer_date - d.order_purchase_timestamp).dt.total_seconds() / 86400
d["promised_days"] = (d.order_estimated_delivery_date - d.order_purchase_timestamp).dt.total_seconds() / 86400
d["gap_days"]      = (d.order_delivered_customer_date - d.order_estimated_delivery_date).dt.total_seconds() / 86400
print(f"delivered orders analysed = {len(d):,}")
print(d[["actual_days", "promised_days", "gap_days"]].describe(percentiles=[.05, .25, .5, .75, .95]).round(2).to_string())
print(f"\nLATE (gap>0) = {(d.gap_days > 0).mean() * 100:.2f}%   EARLY/ON-TIME = {(d.gap_days <= 0).mean() * 100:.2f}%")
print(f"median slack (days early) = {-d.gap_days.median():.1f}")

hdr("7. SCORE BY DELIVERY OUTCOME  (hypothesis C setup)")
dr = d.merge(revs[["order_id", "review_score", "review_creation_date"]], on="order_id", how="inner")
bins = [-1e9, -15, -7, -3, 0, 3, 7, 15, 1e9]
labs = ["15d+ early", "7-15d early", "3-7d early", "0-3d early", "0-3d LATE", "3-7d LATE", "7-15d LATE", "15d+ LATE"]
dr["bucket"] = pd.cut(dr.gap_days, bins=bins, labels=labs)
g = dr.groupby("bucket", observed=True).agg(n=("review_score", "size"),
        mean_score=("review_score", "mean"),
        pct_1star=("review_score", lambda s: (s == 1).mean() * 100))
print(g.round(2).to_string())

hdr("8. SCORE BY ORDER STATUS  (non-delivery as a separate failure mode)")
os_ = orders.merge(revs[["order_id", "review_score"]], on="order_id", how="inner")
print(os_.groupby("order_status").agg(n=("review_score", "size"), mean_score=("review_score", "mean"),
      pct_1star=("review_score", lambda s: (s == 1).mean() * 100)).round(2).sort_values("n", ascending=False).to_string())

hdr("9. *** SURVEY TIMING ARTIFACT ***  (hypothesis B - the crown jewel)")
dr["review_before_delivery"] = dr.review_creation_date < dr.order_delivered_customer_date
n_before = dr.review_before_delivery.sum()
print(f"reviews CREATED BEFORE the product arrived: {n_before:,} of {len(dr):,} ({n_before / len(dr) * 100:.2f}%)")
print("\nscore comparison:")
print(dr.groupby("review_before_delivery").agg(n=("review_score", "size"),
      mean_score=("review_score", "mean"),
      pct_1star=("review_score", lambda s: (s == 1).mean() * 100)).round(2).to_string())
print(f"\nshare of ALL 1-star reviews that were written pre-delivery: "
      f"{dr[dr.review_score == 1].review_before_delivery.mean() * 100:.1f}%")
print("\ndoes the survey fire at the ETA? (review_creation - estimated_delivery, days, LATE orders):")
dr["surv_vs_eta"] = (dr.review_creation_date - dr.order_estimated_delivery_date).dt.total_seconds() / 86400
print(dr[dr.gap_days > 0].surv_vs_eta.describe(percentiles=[.25, .5, .75]).round(2).to_string())

hdr("10. LEAD-TIME DECOMPOSITION  (where does the time actually go?)")
d["t_approve"] = (d.order_approved_at - d.order_purchase_timestamp).dt.total_seconds() / 86400
d["t_handoff"] = (d.order_delivered_carrier_date - d.order_approved_at).dt.total_seconds() / 86400
d["t_transit"] = (d.order_delivered_customer_date - d.order_delivered_carrier_date).dt.total_seconds() / 86400
late = d.gap_days > 0
print("             on-time/early       LATE      delta")
for c in ["t_approve", "t_handoff", "t_transit", "actual_days"]:
    a, b = d.loc[~late, c].median(), d.loc[late, c].median()
    print(f"{c:<12} {a:>12.2f} {b:>10.2f} {b - a:>10.2f}")

hdr("11. REPEAT CUSTOMERS")
print(f"customer_id unique   = {cust.customer_id.nunique():,}")
print(f"customer_unique_id   = {cust.customer_unique_id.nunique():,}")
vc = cust.customer_unique_id.value_counts()
print(f"people with >1 order = {(vc > 1).sum():,}  ({(vc > 1).mean() * 100:.2f}% of people)")
print(f"orders from repeaters= {vc[vc > 1].sum():,}  ({vc[vc > 1].sum() / len(cust) * 100:.2f}% of orders)")

hdr("12. PAYMENTS")
pt = pays.payment_type.value_counts()
print(pd.DataFrame({"n": pt, "pct": (pt / len(pays) * 100).round(2)}).to_string())
print("\nvalue + installments by type:")
print(pays.groupby("payment_type").agg(n=("payment_value", "size"), mean_value=("payment_value", "mean"),
      median_value=("payment_value", "median"), mean_inst=("payment_installments", "mean")).round(2).to_string())
first_pay = pays.sort_values("payment_sequential").groupby("order_id").payment_type.first()
oa = orders.set_index("order_id").join(first_pay.rename("ptype"))
oa["approve_lag_h"] = (oa.order_approved_at - oa.order_purchase_timestamp).dt.total_seconds() / 3600
print("\napproval lag (hours) + failure rate by payment type:")
print(oa.groupby("ptype").agg(n=("approve_lag_h", "size"), median_lag_h=("approve_lag_h", "median"),
      mean_lag_h=("approve_lag_h", "mean"),
      pct_not_delivered=("order_status", lambda s: (s != "delivered").mean() * 100)).round(2).to_string())

hdr("13. GEOGRAPHY CONCENTRATION")
print("top customer states:"); print((cust.customer_state.value_counts(normalize=True).head(6) * 100).round(2).to_string())
print("\ntop seller states:");  print((sellers.seller_state.value_counts(normalize=True).head(6) * 100).round(2).to_string())
print(f"\ngeolocation: {len(geo):,} rows / {geo.geolocation_zip_code_prefix.nunique():,} unique prefixes "
      f"= {len(geo) / geo.geolocation_zip_code_prefix.nunique():.1f} rows per prefix")

hdr("14. CATEGORY COVERAGE")
print(f"products missing category = {prods.product_category_name.isna().sum():,}")
print(f"distinct categories in products = {prods.product_category_name.nunique()}  |  translation rows = {len(trans)}")
miss = set(prods.product_category_name.dropna()) - set(trans.product_category_name)
print(f"categories with NO english translation = {len(miss)}: {sorted(miss)}")
