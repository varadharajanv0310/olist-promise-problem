"""
PHASE 1 - Cleaning and the analytical base table.

Produces exactly one row per order in data/processed/orders_analytical.parquet. Every downstream
question reads from this file, so every cleaning decision is made once, here, and logged.

Cleaning decisions (each is defended in the notebook's cleaning section):
  C1  Reviews are deduped to one per order - 827 duplicate review_ids and 555 orders carry more
      than one survey. Zero fully-duplicated rows, so these are genuine repeat surveys, not a copy
      error. Keep the FIRST survey sent, since that is the one the trigger rule generated.
  C2  Order items / payments / reviews are LEFT joined. 775 orders have no line items at all and
      they are overwhelmingly the canceled and unavailable ones - an inner join would silently
      delete the platform's worst-performing orders from every revenue figure.
  C3  Category translation covers 71 of the 73 categories present. `pc_gamer` and
      `portateis_cozinha_e_preparadores_de_alimentos` are hand-added.
  C4  Geolocation is 52.6 rows per zip prefix, so it is collapsed to one mean lat/lng per prefix
      and clipped to Brazil's bounding box to drop bad readings before any distance maths.
  C5  A trend window flag marks Jan 2017 - Aug 2018. The 2016 head (4, 0, 1 orders) and the
      Sep/Oct 2018 tail (16, 4) are export artifacts and must never appear in a time series.
  C6  `not_defined` payments (3 records, R$0.00, all undelivered) are flagged, not silently kept.
  C7  Delivery timings are only computed for orders that actually reached the customer; everything
      else stays null rather than being imputed to zero.
"""
import numpy as np, pandas as pd, pathlib, json

ROOT = pathlib.Path(r"D:\Data Analytics Hackathon - Gradient")
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
LOG = {}


def log(k, v):
    LOG[k] = v
    print(f"  {k:<48} {v}")


def step(t):
    print(f"\n{'-' * 78}\n{t}\n{'-' * 78}")


# ══════════════════════════════════════════════════════════════════ LOAD
step("LOADING RAW")
DATES_O = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
           "order_delivered_customer_date", "order_estimated_delivery_date"]
orders  = pd.read_csv(RAW / "orders.csv", parse_dates=DATES_O)
items   = pd.read_csv(RAW / "order_items.csv")
pays    = pd.read_csv(RAW / "order_payments.csv")
revs    = pd.read_csv(RAW / "order_reviews.csv", parse_dates=["review_creation_date", "review_answer_timestamp"])
cust    = pd.read_csv(RAW / "customers.csv")
prods   = pd.read_csv(RAW / "products.csv")
sellers = pd.read_csv(RAW / "sellers.csv")
geo     = pd.read_csv(RAW / "geolocation.csv")
trans   = pd.read_csv(RAW / "category_translation.csv")
log("orders in", f"{len(orders):,}")

# ══════════════════════════════════════════════════════════════════ C1 reviews
step("C1  DEDUPE REVIEWS")
log("review rows in", f"{len(revs):,}")
log("duplicate review_id", f"{len(revs) - revs.review_id.nunique():,}")
log("orders with >1 survey", f"{(revs.groupby('order_id').size() > 1).sum():,}")
log("fully duplicated rows", f"{revs.duplicated().sum():,}")
revs = revs.sort_values(["order_id", "review_creation_date", "review_answer_timestamp"])
revs = revs.drop_duplicates("order_id", keep="first")
log("review rows out (1 per order)", f"{len(revs):,}")

# ══════════════════════════════════════════════════════════════════ C3 categories
step("C3  CATEGORY TRANSLATION")
MANUAL = {"pc_gamer": "pc_gamer",
          "portateis_cozinha_e_preparadores_de_alimentos": "kitchen_portables_and_food_preparers"}
missing = sorted(set(prods.product_category_name.dropna()) - set(trans.product_category_name))
log("categories with no translation", f"{len(missing)} -> {missing}")
trans = pd.concat([trans, pd.DataFrame(
    {"product_category_name": list(MANUAL), "product_category_name_english": list(MANUAL.values())}
)], ignore_index=True)
prods = prods.merge(trans, on="product_category_name", how="left")
prods["category_en"] = prods.product_category_name_english.fillna("unknown")
log("products with unknown category", f"{(prods.category_en == 'unknown').sum():,}")
prods["product_volume_cm3"] = prods.product_length_cm * prods.product_height_cm * prods.product_width_cm

# ══════════════════════════════════════════════════════════════════ C4 geolocation
step("C4  GEOLOCATION -> ONE POINT PER ZIP PREFIX")
log("geolocation rows in", f"{len(geo):,}")
log("unique zip prefixes", f"{geo.geolocation_zip_code_prefix.nunique():,}")
log("rows per prefix", f"{len(geo) / geo.geolocation_zip_code_prefix.nunique():.1f}")
BBOX = dict(lat_min=-33.75, lat_max=5.28, lng_min=-73.99, lng_max=-34.79)  # Brazil
inside = (geo.geolocation_lat.between(BBOX["lat_min"], BBOX["lat_max"]) &
          geo.geolocation_lng.between(BBOX["lng_min"], BBOX["lng_max"]))
log("readings outside Brazil (dropped)", f"{(~inside).sum():,}")
geo_pt = (geo[inside].groupby("geolocation_zip_code_prefix")
          .agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean")).reset_index())
log("zip prefixes out", f"{len(geo_pt):,}")

# ══════════════════════════════════════════════════════════════════ C2 items
step("C2  AGGREGATE ORDER ITEMS (left join - keep itemless orders)")
log("item rows", f"{len(items):,}")
log("orders present in items", f"{items.order_id.nunique():,}")
log("orders with NO items", f"{len(orders) - items.order_id.nunique():,}")
it = items.merge(prods[["product_id", "category_en", "product_weight_g", "product_volume_cm3"]],
                 on="product_id", how="left")
item_agg = it.groupby("order_id").agg(
    n_items=("order_item_id", "size"),
    n_distinct_products=("product_id", "nunique"),
    n_sellers=("seller_id", "nunique"),
    order_value=("price", "sum"),
    freight_total=("freight_value", "sum"),
    max_item_price=("price", "max"),
    total_weight_g=("product_weight_g", "sum"),
    total_volume_cm3=("product_volume_cm3", "sum"),
).reset_index()
# the "primary" seller/product/category = the one on the most expensive line
primary = (it.sort_values(["order_id", "price"], ascending=[True, False])
           .drop_duplicates("order_id", keep="first")
           [["order_id", "seller_id", "product_id", "category_en"]]
           .rename(columns={"seller_id": "primary_seller_id",
                            "product_id": "primary_product_id",
                            "category_en": "primary_category"}))
item_agg = item_agg.merge(primary, on="order_id", how="left")
log("multi-item orders", f"{(item_agg.n_items > 1).sum():,}")
log("multi-seller orders", f"{(item_agg.n_sellers > 1).sum():,}")

# ══════════════════════════════════════════════════════════════════ C6 payments
step("C6  AGGREGATE PAYMENTS")
log("payment rows", f"{len(pays):,}")
log("not_defined records (flagged)", f"{(pays.payment_type == 'not_defined').sum():,}")
pay_agg = pays.groupby("order_id").agg(
    payment_total=("payment_value", "sum"),
    n_payment_records=("payment_sequential", "size"),
    max_installments=("payment_installments", "max"),
    n_payment_types=("payment_type", "nunique"),
).reset_index()
# "primary" method = the one carrying the largest share of the money, not sequential #1,
# because vouchers frequently occupy sequence 1 on part-voucher orders.
prim_pay = (pays.sort_values(["order_id", "payment_value"], ascending=[True, False])
            .drop_duplicates("order_id", keep="first")[["order_id", "payment_type"]]
            .rename(columns={"payment_type": "payment_type"}))
pay_agg = pay_agg.merge(prim_pay, on="order_id", how="left")
pay_agg["used_voucher"] = pays.assign(v=pays.payment_type.eq("voucher")).groupby("order_id").v.max().values
pay_agg["has_undefined_payment"] = pays.assign(
    v=pays.payment_type.eq("not_defined")).groupby("order_id").v.max().values
log("multi-payment orders", f"{(pay_agg.n_payment_records > 1).sum():,}")

# ══════════════════════════════════════════════════════════════════ ASSEMBLE
step("ASSEMBLING ORDER-LEVEL TABLE")
df = orders.merge(cust, on="customer_id", how="left")
for name, tbl in [("items", item_agg), ("payments", pay_agg)]:
    before = len(df)
    df = df.merge(tbl, on="order_id", how="left")
    assert len(df) == before, f"{name} join changed the grain"
df = df.merge(revs[["order_id", "review_id", "review_score", "review_creation_date",
                    "review_answer_timestamp", "review_comment_title", "review_comment_message"]],
              on="order_id", how="left")
assert len(df) == len(orders) and df.order_id.is_unique, "grain broken"
log("rows after joins (must be 99,441)", f"{len(df):,}")

# ── seller + geo ──────────────────────────────────────────────────────────
df = df.merge(sellers.rename(columns={"seller_id": "primary_seller_id"}),
              on="primary_seller_id", how="left")
df = df.merge(geo_pt.rename(columns={"geolocation_zip_code_prefix": "customer_zip_code_prefix",
                                     "lat": "cust_lat", "lng": "cust_lng"}),
              on="customer_zip_code_prefix", how="left")
df = df.merge(geo_pt.rename(columns={"geolocation_zip_code_prefix": "seller_zip_code_prefix",
                                     "lat": "sell_lat", "lng": "sell_lng"}),
              on="seller_zip_code_prefix", how="left")
log("orders missing customer geo", f"{df.cust_lat.isna().sum():,}")
log("orders missing seller geo", f"{df.sell_lat.isna().sum():,}")


def haversine(lat1, lng1, lat2, lng2):
    R_KM = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lng2 - lng1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R_KM * np.arcsin(np.sqrt(a))


df["seller_customer_km"] = haversine(df.sell_lat, df.sell_lng, df.cust_lat, df.cust_lng)
log("orders with a distance", f"{df.seller_customer_km.notna().sum():,}")
log("median seller->customer km", f"{df.seller_customer_km.median():.0f}")

# ══════════════════════════════════════════════════════════════════ C7 timings
step("C7  DERIVED TIMING FEATURES (delivered orders only)")
delivered = df.order_delivered_customer_date.notna()
DAY = 86400
df["actual_days"]   = np.where(delivered, (df.order_delivered_customer_date - df.order_purchase_timestamp).dt.total_seconds() / DAY, np.nan)
df["promised_days"] = (df.order_estimated_delivery_date - df.order_purchase_timestamp).dt.total_seconds() / DAY
df["gap_days"]      = np.where(delivered, (df.order_delivered_customer_date - df.order_estimated_delivery_date).dt.total_seconds() / DAY, np.nan)
df["t_approve"]     = (df.order_approved_at - df.order_purchase_timestamp).dt.total_seconds() / DAY
df["t_handoff"]     = (df.order_delivered_carrier_date - df.order_approved_at).dt.total_seconds() / DAY
df["t_transit"]     = np.where(delivered, (df.order_delivered_customer_date - df.order_delivered_carrier_date).dt.total_seconds() / DAY, np.nan)
df["is_delivered"]  = df.order_status.eq("delivered")
df["is_late"]       = np.where(df.gap_days.notna(), df.gap_days > 0, np.nan)
df["late_bucket"]   = pd.cut(df.gap_days, [-1e9, -15, -7, -3, 0, 3, 7, 15, 1e9],
                             labels=["15d+ early", "7-15d early", "3-7d early", "0-3d early",
                                     "0-3d late", "3-7d late", "7-15d late", "15d+ late"])
log("delivered w/ timings", f"{df.actual_days.notna().sum():,}")
log("late share of delivered", f"{df.is_late.mean() * 100:.2f}%")

# ══════════════════════════════════════════════════════════════════ economics + review
step("ECONOMICS, REVIEW AND CUSTOMER FEATURES")
df["freight_ratio"] = np.where(df.order_value > 0, df.freight_total / df.order_value, np.nan)
df["aov_per_item"]  = np.where(df.n_items > 0, df.order_value / df.n_items, np.nan)
df["has_comment"]   = df.review_comment_message.notna()
df["is_one_star"]   = np.where(df.review_score.notna(), df.review_score == 1, np.nan)
df["is_low_score"]  = np.where(df.review_score.notna(), df.review_score <= 2, np.nan)
df["pre_delivery_review"] = np.where(
    df.review_creation_date.notna() & df.order_delivered_customer_date.notna(),
    df.review_creation_date < df.order_delivered_customer_date, np.nan)
log("orders with a review", f"{df.review_score.notna().sum():,}")
log("pre-delivery reviews", f"{np.nansum(df.pre_delivery_review):,.0f}")

cnt = df.groupby("customer_unique_id").order_id.transform("size")
df["customer_total_orders"] = cnt
df["is_repeat_customer"] = cnt > 1
df["customer_order_seq"] = df.sort_values("order_purchase_timestamp").groupby("customer_unique_id").cumcount() + 1
log("repeat customers (people)", f"{(df.groupby('customer_unique_id').size() > 1).sum():,}")
log("orders from repeat customers", f"{df.is_repeat_customer.sum():,}")

# ══════════════════════════════════════════════════════════════════ C5 window
step("C5  TREND WINDOW FLAG")
df["order_ym"] = df.order_purchase_timestamp.dt.to_period("M").astype(str)
df["in_trend_window"] = df.order_purchase_timestamp.between("2017-01-01", "2018-08-31 23:59:59")
log("orders in Jan2017-Aug2018 window", f"{df.in_trend_window.sum():,} "
                                        f"({df.in_trend_window.mean() * 100:.1f}%)")
log("orders excluded as edge artifacts", f"{(~df.in_trend_window).sum():,}")

# ══════════════════════════════════════════════════════════════════ SAVE
step("VALIDATION + SAVE")
assert len(df) == 99441 and df.order_id.is_unique
assert df.review_score.dropna().between(1, 5).all()
assert (df.n_items.dropna() > 0).all()
bad_seq = (df.order_delivered_customer_date < df.order_delivered_carrier_date).sum()
log("orders delivered BEFORE carrier pickup", f"{bad_seq:,}  (flagged, not dropped)")
df["timestamp_anomaly"] = (df.order_delivered_customer_date < df.order_delivered_carrier_date).fillna(False)

df.to_parquet(OUT / "orders_analytical.parquet", index=False)
LOG["output_rows"], LOG["output_cols"] = len(df), df.shape[1]
(OUT / "cleaning_log.json").write_text(json.dumps(LOG, indent=2), encoding="utf-8")
print(f"\n  -> {OUT / 'orders_analytical.parquet'}  ({len(df):,} rows x {df.shape[1]} cols)")
print(f"  -> {OUT / 'cleaning_log.json'}")
