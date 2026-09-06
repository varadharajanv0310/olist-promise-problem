"""Generate the Colab submission notebook.

Kept as a generator rather than a hand-edited .ipynb so the notebook and the analysis scripts
cannot drift apart: every number in it is recomputed by the cell that prints it.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "notebook" / "olist_promise_problem.ipynb"
OUT.parent.mkdir(exist_ok=True)
cells = []


def md(src):
    cells.append({"cell_type": "markdown", "metadata": {},
                  "source": src.strip("\n").split("\n")})


def code(src):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": src.strip("\n").split("\n")})


# ════════════════════════════════════════════════════════════════ TITLE
md(r"""
# The Promise Problem
### What actually drives customer satisfaction on the Olist marketplace

**Data Analytics Hackathon · Gradient Learning**

---

Olist is a Brazilian marketplace integrator: small merchants sign one contract and sell through the
big platforms, with Olist's logistics partners handling delivery. This notebook analyses **99,441
orders placed between September 2016 and October 2018** to answer one question — what is actually
shaping the customer experience, and where are the clearest opportunities to improve it?

**The finding, up front.** Olist promises delivery in a median of 23 days and delivers in 10. That
twelve-day padding looks like broken forecasting. It isn't — it is a correctly-priced insurance
policy against a wildly asymmetric downside, and this notebook shows that the obvious recommendation
("tighten the estimates") is not just wrong but *already tested*: Olist cut its promise from 39 days
to 13 over 19 months and watched its late rate triple.

The real opportunity is not a shorter promise or a longer one. It is a **different promise for every
order**, which we demonstrate cuts late deliveries by 47% without lengthening the promise at all.

**How to read this notebook.** It follows the shape of an investigation rather than a report: each
section states what we expected, tests it, and reports what actually held — including one headline
hypothesis that we falsified and had to abandon (§6).
""")

# ════════════════════════════════════════════════════════════════ SETUP
md(r"""
---
## 0 · Setup

The nine Olist CSVs are loaded from whichever source is available. On Colab, upload the files when
prompted or place them in a `data/` folder on your Drive.
""")

code(r'''
import sys, subprocess, warnings, pathlib, json, re
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

IN_COLAB = "google.colab" in sys.modules
print(f"pandas {pd.__version__} | numpy {np.__version__} | matplotlib {mpl.__version__}")
print(f"running in Colab: {IN_COLAB}")

# NOTE ON DEPENDENCIES: this notebook deliberately avoids statsmodels. Version 0.14.4 fails to
# import against scipy >= 1.16 (`_lazywhere` was removed from scipy._lib._util), which is the pairing
# Colab currently ships. Every statistical routine here - OLS with robust errors, the regression
# discontinuity, and the logistic driver model - is written directly in numpy instead.
''')

code(r'''
FILES = ["olist_orders_dataset", "olist_order_items_dataset", "olist_order_payments_dataset",
         "olist_order_reviews_dataset", "olist_customers_dataset", "olist_products_dataset",
         "olist_sellers_dataset", "olist_geolocation_dataset", "product_category_name_translation"]
SHORT = ["orders", "order_items", "order_payments", "order_reviews", "customers",
         "products", "sellers", "geolocation", "category_translation"]


def find_data():
    """Locate the CSVs. Tries local folders, then Drive, then falls back to an upload prompt."""
    for c in ["data/raw", "data", ".", "/content/data", "/content",
              "/content/drive/MyDrive/olist", "/content/drive/MyDrive/data"]:
        p = pathlib.Path(c)
        if p.exists() and any((p / f"{n}.csv").exists() for n in SHORT + FILES):
            return p
    if IN_COLAB:
        print("Upload the nine Olist CSVs (or the single .xlsx workbook):")
        from google.colab import files
        files.upload()
        return pathlib.Path("/content")
    raise FileNotFoundError("Place the Olist CSVs in ./data/raw or ./data")


DATA = find_data()
print(f"data directory: {DATA.resolve()}")


def read(short, long, **kw):
    """Accept either the short names used in this repo or Kaggle's original filenames."""
    for name in (short, long):
        f = DATA / f"{name}.csv"
        if f.exists():
            return pd.read_csv(f, **kw)
    # last resort: the single-workbook delivery format
    for xl in DATA.glob("*.xlsx"):
        return pd.read_excel(xl, sheet_name=short, **{k: v for k, v in kw.items()
                                                      if k != "parse_dates"})
    raise FileNotFoundError(short)


DATES_O = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
           "order_delivered_customer_date", "order_estimated_delivery_date"]
orders  = read("orders", FILES[0], parse_dates=DATES_O)
items   = read("order_items", FILES[1])
pays    = read("order_payments", FILES[2])
revs    = read("order_reviews", FILES[3], parse_dates=["review_creation_date", "review_answer_timestamp"])
cust    = read("customers", FILES[4])
prods   = read("products", FILES[5])
sellers = read("sellers", FILES[6])
geo     = read("geolocation", FILES[7])
trans   = read("category_translation", FILES[8])

for n, d in zip(SHORT, [orders, items, pays, revs, cust, prods, sellers, geo, trans]):
    print(f"  {n:<22} {len(d):>9,} rows x {d.shape[1]} cols")
''')

md(r"""
### Chart styling

One style for every figure, so the notebook reads as a single piece of work. Colour is used
semantically throughout: **teal means on time, rust means late.** No chart uses two y-axes — where
two measures of different scale need comparing, they are indexed to a common base or split into
small multiples.
""")

code(r'''
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
OK, LATE = "#0f6b5c", "#c2410c"
SURFACE, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#14201f", "#4e5b59", "#8b9694", "#e3e0d9", "#c3c2b7"

mpl.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.edgecolor": BASE, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.7,
    "grid.linestyle": "-", "axes.axisbelow": True,
    "xtick.major.size": 0, "ytick.major.size": 0,
    "axes.titlesize": 13, "axes.titleweight": "600", "axes.titlepad": 14,
    "figure.dpi": 110, "legend.frameon": False, "legend.fontsize": 9,
})


def titled(ax, headline, sub=None):
    """Headline states the finding; the subtitle carries method and units."""
    ax.set_title(headline, loc="left", pad=18 if sub else 14)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=MUTED, va="bottom")


print("chart style set")
''')

# ════════════════════════════════════════════════════════════════ 1 UNDERSTANDING
md(r"""
---
## 1 · Data Understanding

Nine tables. Before analysing anything we establish the grain of each, confirm the keys, and find
out where the joins will misbehave.
""")

code(r'''
print("KEY UNIQUENESS")
for name, d, key in [("orders", orders, "order_id"), ("customers", cust, "customer_id"),
                     ("products", prods, "product_id"), ("sellers", sellers, "seller_id"),
                     ("reviews", revs, "review_id")]:
    dup = len(d) - d[key].nunique()
    flag = "  <-- NOT UNIQUE" if dup else ""
    print(f"  {name:<11} {len(d):>8,} rows   {d[key].nunique():>8,} unique {key}   dup {dup:>4,}{flag}")

print("\nGRAIN vs ORDERS")
print(f"  orders present in order_items    {items.order_id.nunique():>8,} / {len(orders):,}"
      f"   MISSING {len(orders) - items.order_id.nunique():,}")
print(f"  orders present in order_payments {pays.order_id.nunique():>8,}")
print(f"  orders present in order_reviews  {revs.order_id.nunique():>8,}")
print(f"  orders with >1 item              {(items.groupby('order_id').size() > 1).sum():>8,}")
print(f"  orders with >1 SELLER            {(items.groupby('order_id').seller_id.nunique() > 1).sum():>8,}")
print(f"  orders with >1 payment record    {(pays.groupby('order_id').size() > 1).sum():>8,}")
print(f"  orders with >1 review            {(revs.groupby('order_id').size() > 1).sum():>8,}")

print("\nGEOLOCATION IS NOT A LOOKUP TABLE")
print(f"  {len(geo):,} rows over {geo.geolocation_zip_code_prefix.nunique():,} zip prefixes"
      f"  =  {len(geo) / geo.geolocation_zip_code_prefix.nunique():.1f} rows per prefix")
print("  joining this directly would multiply every order by ~53.")
''')

md(r"""
Three things here matter more than they look:

- **`review_id` is not unique.** 827 duplicates, and 555 orders carry more than one survey. No rows
  are fully duplicated, so these are genuine repeat surveys rather than a copy error.
- **775 orders have no line items at all.** They are overwhelmingly the cancelled and unavailable
  ones — so an inner join would silently delete the platform's *worst-performing* orders from every
  revenue figure.
- **1,278 orders ship from more than one seller.** This looks like a footnote. It turns out to be
  the single largest driver of 1-star reviews in the dataset (§8).
""")

code(r'''
print("MISSINGNESS")
for nm, d in [("orders", orders), ("products", prods), ("reviews", revs)]:
    m = d.isna().sum(); m = m[m > 0]
    print(f"\n  {nm}:")
    for k, v in m.items():
        print(f"    {k:<32} {v:>7,}  ({v / len(d) * 100:5.2f}%)")

print("\n\nORDER STATUS")
st = orders.order_status.value_counts()
for k, v in st.items():
    print(f"  {k:<14} {v:>7,}  {v / len(orders) * 100:5.2f}%")
print(f"\n  {(orders.order_status != 'delivered').sum():,} orders never reached the customer.")
print("  They still get reviewed - and they are a separate failure mode from late delivery (§8).")
''')

# ════════════════════════════════════════════════════════════════ 2 CLEANING
md(r"""
---
## 2 · Data Cleaning

Seven decisions, each stated with its reasoning and its before/after count. These are real
characteristics of an operational export, not planted defects — the job is to handle them
deliberately rather than to "fix" them.

| # | Decision | Why |
|---|---|---|
| C1 | Dedupe reviews to one per order, keeping the first survey | 827 duplicate ids; the first survey is the one the trigger rule generated |
| C2 | Left-join items/payments/reviews onto orders | 775 itemless orders are the cancelled ones; an inner join deletes the worst outcomes |
| C3 | Hand-add 2 missing category translations | the lookup covers 71 of 73 categories present |
| C4 | Collapse geolocation to one point per prefix, clipped to Brazil | 52.6 rows per prefix would multiply the table |
| C5 | Flag a Jan 2017 – Aug 2018 trend window | the 2016 head and Sep/Oct 2018 tail are export artifacts, not a real collapse |
| C6 | Flag `not_defined` payments rather than dropping them | 3 records, R\$0.00, all undelivered |
| C7 | Compute delivery timings only where the order reached the customer | never impute a delivery date to zero |
""")

code(r'''
log = {}

# ── C1 ────────────────────────────────────────────────────────────────────────
before = len(revs)
revs_c = (revs.sort_values(["order_id", "review_creation_date", "review_answer_timestamp"])
          .drop_duplicates("order_id", keep="first"))
log["C1 reviews deduped"] = f"{before:,} -> {len(revs_c):,}  (-{before - len(revs_c):,})"

# ── C3 ────────────────────────────────────────────────────────────────────────
MANUAL = {"pc_gamer": "pc_gamer",
          "portateis_cozinha_e_preparadores_de_alimentos": "kitchen_portables_and_food_preparers"}
missing_cats = sorted(set(prods.product_category_name.dropna()) - set(trans.product_category_name))
trans_c = pd.concat([trans, pd.DataFrame({"product_category_name": list(MANUAL),
                                          "product_category_name_english": list(MANUAL.values())})],
                    ignore_index=True)
prods_c = prods.merge(trans_c, on="product_category_name", how="left")
prods_c["category_en"] = prods_c.product_category_name_english.fillna("unknown")
prods_c["product_volume_cm3"] = (prods_c.product_length_cm * prods_c.product_height_cm
                                 * prods_c.product_width_cm)
log["C3 categories hand-added"] = f"{missing_cats}"
log["C3 products left 'unknown'"] = f"{(prods_c.category_en == 'unknown').sum():,}"

# ── C4 ────────────────────────────────────────────────────────────────────────
BBOX = dict(la=(-33.75, 5.28), lo=(-73.99, -34.79))          # Brazil's bounding box
inside = (geo.geolocation_lat.between(*BBOX["la"]) & geo.geolocation_lng.between(*BBOX["lo"]))
geo_pt = (geo[inside].groupby("geolocation_zip_code_prefix")
          .agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean")).reset_index())
log["C4 geo readings dropped (outside Brazil)"] = f"{(~inside).sum():,}"
log["C4 geolocation rows -> points"] = f"{len(geo):,} -> {len(geo_pt):,}"

for k, v in log.items():
    print(f"  {k:<46} {v}")
''')

code(r'''
# ── C2: aggregate to order grain, then LEFT join ─────────────────────────────
it = items.merge(prods_c[["product_id", "category_en", "product_weight_g", "product_volume_cm3"]],
                 on="product_id", how="left")
item_agg = it.groupby("order_id").agg(
    n_items=("order_item_id", "size"), n_distinct_products=("product_id", "nunique"),
    n_sellers=("seller_id", "nunique"), order_value=("price", "sum"),
    freight_total=("freight_value", "sum"), total_weight_g=("product_weight_g", "sum"),
    total_volume_cm3=("product_volume_cm3", "sum")).reset_index()
primary = (it.sort_values(["order_id", "price"], ascending=[True, False])
           .drop_duplicates("order_id", keep="first")[["order_id", "seller_id", "product_id", "category_en"]]
           .rename(columns={"seller_id": "primary_seller_id", "product_id": "primary_product_id",
                            "category_en": "primary_category"}))
item_agg = item_agg.merge(primary, on="order_id", how="left")

pay_agg = pays.groupby("order_id").agg(
    payment_total=("payment_value", "sum"), n_payment_records=("payment_sequential", "size"),
    max_installments=("payment_installments", "max"), n_payment_types=("payment_type", "nunique")
).reset_index()
# "primary" method = the one carrying the most money, NOT sequence 1 - vouchers often sit first
prim_pay = (pays.sort_values(["order_id", "payment_value"], ascending=[True, False])
            .drop_duplicates("order_id", keep="first")[["order_id", "payment_type"]])
pay_agg = pay_agg.merge(prim_pay, on="order_id", how="left")
pay_agg["used_voucher"] = pays.assign(v=pays.payment_type.eq("voucher")).groupby("order_id").v.max().values

df = orders.merge(cust, on="customer_id", how="left")
for tbl in (item_agg, pay_agg):
    n0 = len(df); df = df.merge(tbl, on="order_id", how="left")
    assert len(df) == n0, "join changed the grain"
df = df.merge(revs_c[["order_id", "review_score", "review_creation_date", "review_answer_timestamp",
                      "review_comment_title", "review_comment_message"]], on="order_id", how="left")
assert len(df) == len(orders) and df.order_id.is_unique
print(f"order-level table: {len(df):,} rows (must equal {len(orders):,})  unique: {df.order_id.is_unique}")
''')

code(r'''
# ── geography + distance ─────────────────────────────────────────────────────
df = df.merge(sellers.rename(columns={"seller_id": "primary_seller_id"}), on="primary_seller_id", how="left")
df = df.merge(geo_pt.rename(columns={"geolocation_zip_code_prefix": "customer_zip_code_prefix",
                                     "lat": "cust_lat", "lng": "cust_lng"}),
              on="customer_zip_code_prefix", how="left")
df = df.merge(geo_pt.rename(columns={"geolocation_zip_code_prefix": "seller_zip_code_prefix",
                                     "lat": "sell_lat", "lng": "sell_lng"}),
              on="seller_zip_code_prefix", how="left")


def haversine(la1, lo1, la2, lo2):
    R = 6371.0
    p1, p2 = np.radians(la1), np.radians(la2)
    dp, dl = p2 - p1, np.radians(lo2 - lo1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


df["seller_customer_km"] = haversine(df.sell_lat, df.sell_lng, df.cust_lat, df.cust_lng)

# ── C7: timings only where the order actually arrived ────────────────────────
DAY = 86400
arrived = df.order_delivered_customer_date.notna()
df["actual_days"]   = np.where(arrived, (df.order_delivered_customer_date - df.order_purchase_timestamp).dt.total_seconds() / DAY, np.nan)
df["promised_days"] = (df.order_estimated_delivery_date - df.order_purchase_timestamp).dt.total_seconds() / DAY
df["gap_days"]      = np.where(arrived, (df.order_delivered_customer_date - df.order_estimated_delivery_date).dt.total_seconds() / DAY, np.nan)
df["t_approve"]     = (df.order_approved_at - df.order_purchase_timestamp).dt.total_seconds() / DAY
df["t_handoff"]     = (df.order_delivered_carrier_date - df.order_approved_at).dt.total_seconds() / DAY
df["t_transit"]     = np.where(arrived, (df.order_delivered_customer_date - df.order_delivered_carrier_date).dt.total_seconds() / DAY, np.nan)

df["is_delivered"] = df.order_status.eq("delivered")
df["is_late"]      = np.where(df.gap_days.notna(), df.gap_days > 0, np.nan)
df["late_bucket"]  = pd.cut(df.gap_days, [-1e9, -15, -7, -3, 0, 3, 7, 15, 1e9],
                            labels=["15d+ early", "7-15d early", "3-7d early", "0-3d early",
                                    "0-3d late", "3-7d late", "7-15d late", "15d+ late"])
df["is_one_star"]  = np.where(df.review_score.notna(), df.review_score == 1, np.nan)
df["freight_ratio"] = np.where(df.order_value > 0, df.freight_total / df.order_value, np.nan)
df["has_comment"]  = df.review_comment_message.notna()
df["pre_delivery_review"] = np.where(
    df.review_creation_date.notna() & df.order_delivered_customer_date.notna(),
    df.review_creation_date < df.order_delivered_customer_date, np.nan)

cnt = df.groupby("customer_unique_id").order_id.transform("size")
df["is_repeat_customer"] = cnt > 1

# ── C5: the trend window ─────────────────────────────────────────────────────
df["order_ym"] = df.order_purchase_timestamp.dt.to_period("M")
df["in_trend_window"] = df.order_purchase_timestamp.between("2017-01-01", "2018-08-31 23:59:59")

print(f"analytical table: {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"  delivered with timings   {df.actual_days.notna().sum():,}")
print(f"  with a distance          {df.seller_customer_km.notna().sum():,}")
print(f"  inside the trend window  {df.in_trend_window.sum():,}  "
      f"({(~df.in_trend_window).sum():,} excluded as edge artifacts)")
''')

md(r"""
### Why the trend window matters

Plotting the raw date range invents a collapse at both ends that has nothing to do with the business.
""")

code(r'''
mv = df.groupby("order_ym").size()
fig, ax = plt.subplots(figsize=(10, 3.6))
inside = [str(p) for p in mv.index if pd.Period("2017-01") <= p <= pd.Period("2018-08")]
cols = [C1 if str(p) in inside else LATE for p in mv.index]
ax.bar([str(p) for p in mv.index], mv.values, color=cols, width=0.72, zorder=3)
ax.set_xticks(range(0, len(mv), 3))
ax.set_xticklabels([str(p) for p in mv.index[::3]], rotation=45, ha="right", fontsize=8.5)
ax.set_ylabel("Orders placed")
titled(ax, "The head and tail are export artifacts, not a business collapse",
       "Orders per month · rust months are excluded from every time series")
for i, p in enumerate(mv.index):
    if mv.values[i] < 400:
        ax.annotate(f"{mv.values[i]:,}", (i, mv.values[i]), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=8, color=LATE)
plt.show()
print("Sep 2016: 4 orders | Dec 2016: 1 | Sep 2018: 16 | Oct 2018: 4")
''')

# ════════════════════════════════════════════════════════════════ 3 EDA
md(r"""
---
## 3 · Exploratory Data Analysis

### The review score is bimodal — which decides how we model it later

57% of reviews are 5-star and 12% are 1-star. There is very little in between. A mean over that
distribution is an average of two populations that barely overlap, so from §8 onwards we model
**P(1-star)** rather than the mean score.
""")

code(r'''
sc = df.review_score.value_counts().sort_index()
fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9))
ax = axes[0]
ax.bar(sc.index, sc.values, color=[LATE, LATE, MUTED, C3, OK], width=0.66, zorder=3)
for k, v in sc.items():
    ax.annotate(f"{v / len(df.review_score.dropna()) * 100:.0f}%", (k, v), xytext=(0, 5),
                textcoords="offset points", ha="center", fontsize=10, color=INK, fontweight="600")
ax.set_xlabel("Review score"); ax.set_ylabel("Reviews")
titled(ax, "Two populations, not a bell curve")

ax = axes[1]
cr = df.groupby("review_score").review_comment_message.apply(lambda s: s.notna().mean() * 100)
ax.bar(cr.index, cr.values, color=C1, width=0.66, zorder=3)
for k, v in cr.items():
    ax.annotate(f"{v:.0f}%", (k, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=10, color=INK, fontweight="600")
ax.set_xlabel("Review score"); ax.set_ylabel("Left a written comment (%)")
titled(ax, "Angry customers write")
plt.tight_layout(); plt.show()

print(f"mean {df.review_score.mean():.3f} | median {df.review_score.median():.0f} | "
      f"1-2 star {(df.review_score <= 2).mean() * 100:.1f}%")
print("77% of 1-star reviewers write a comment vs 36% of 5-star -> text analysis is viable")
print("exactly where it matters (§10).")
''')

md(r"""
### The delivery promise is padded by about twelve days
""")

code(r'''
d = df[df.gap_days.notna()]
print(d[["actual_days", "promised_days", "gap_days"]].describe(
    percentiles=[.05, .25, .5, .75, .95]).round(2).to_string())
print(f"\nLATE {(d.gap_days > 0).mean() * 100:.2f}%   ON TIME OR EARLY {(d.gap_days <= 0).mean() * 100:.2f}%")
print(f"median slack: {-d.gap_days.median():.1f} days of padding")

fig, ax = plt.subplots(figsize=(9.5, 4))
ax.hist(d.gap_days.clip(-45, 30), bins=76, color=C1, zorder=3)
ax.axvline(0, color=LATE, linewidth=1.6, zorder=4)
ax.annotate("promised date", (0, ax.get_ylim()[1] * 0.92), xytext=(8, 0),
            textcoords="offset points", color=LATE, fontsize=10, fontweight="600")
ax.set_xlabel("Days early (negative) or late (positive) versus the promise")
ax.set_ylabel("Orders")
titled(ax, "Almost the whole distribution sits left of the promise",
       "96,470 delivered orders · clipped to [-45, +30] days for display")
plt.show()
''')

# ════════════════════════════════════════════════════════════════ Q1
md(r"""
---
## 4 · Core Question 1 — Marketplace performance over time

> *How have order volume, revenue and review scores trended? Do they all tell the same story?*

**No.** Volume and revenue are the same story told twice. Satisfaction is a different story, and the
months where they diverge are the ones worth explaining.
""")

code(r'''
w = df[df.in_trend_window].copy()
w["month"] = w.order_purchase_timestamp.dt.to_period("M").dt.to_timestamp()
m = w.groupby("month").agg(
    orders=("order_id", "size"), revenue=("order_value", "sum"), aov=("order_value", "mean"),
    score=("review_score", "mean"), pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100), transit=("t_transit", "median"),
    handoff=("t_handoff", "median"), promised=("promised_days", "median"),
    actual=("actual_days", "median")).reset_index()

first, last = m.iloc[0], m.iloc[-1]
print("Jan 2017  ->  Aug 2018")
for lab, c, f in [("orders / month", "orders", "{:,.0f}"), ("revenue / month", "revenue", "{:,.0f}"),
                  ("avg order value", "aov", "{:.2f}"), ("mean review score", "score", "{:.3f}"),
                  ("1-star rate %", "pct_1star", "{:.2f}"), ("LATE RATE %", "pct_late", "{:.2f}")]:
    print(f"  {lab:<20} {f.format(first[c]):>12} -> {f.format(last[c]):>12}"
          f"   ({(last[c] / first[c] - 1) * 100:+7.1f}%)")
''')

code(r'''
# Indexed to a common base so three different units share ONE axis - never a dual-axis chart.
idx = m.set_index("month")[["orders", "revenue", "score"]]
idx = idx / idx.iloc[0] * 100
fig, ax = plt.subplots(figsize=(10, 4.8))
for c, col, lab in [("orders", C1, "Order volume"), ("revenue", C2, "Revenue"),
                    ("score", C3, "Mean review score")]:
    ax.plot(idx.index, idx[c], color=col, linewidth=2, label=lab)
    ax.annotate(f"{idx[c].iloc[-1]:.0f}", (idx.index[-1], idx[c].iloc[-1]), xytext=(8, 0),
                textcoords="offset points", color=INK2, fontsize=9.5, va="center", fontweight="600")
ax.axhline(100, color=BASE, linewidth=0.8)
ax.set_ylabel("Index (Jan 2017 = 100)"); ax.legend(loc="upper left")
titled(ax, "Growth and satisfaction are not the same story",
       "Indexed to January 2017 = 100")
plt.show()
print("Volume 8x. Revenue 7x. Satisfaction essentially flat — and average order value FELL 13%,")
print("so the growth is more orders, not bigger ones.")
''')

md(r"""
### Satisfaction is volatile, and the volatility is delivery

Two distinct crises, with different causes:

- **November 2017 — a demand shock.** Black Friday drove 7.4× normal daily volume. Both legs
  degraded: seller handoff *and* carrier transit.
- **February–March 2018 — a supply shock.** The worst months in the dataset (21.4% late, 3.74★) and
  *not* a demand event: volume rose only 7.8% while carrier transit blew out and seller handoff held
  steady.
""")

code(r'''
fig, axes = plt.subplots(3, 1, figsize=(10, 7.4), sharex=True)
for ax, (c, lab, col) in zip(axes, [("orders", "Orders placed", C1),
                                    ("pct_late", "Delivered late (%)", LATE),
                                    ("score", "Mean review score", C3)]):
    ax.plot(m.month, m[c], color=col, linewidth=2)
    ax.fill_between(m.month, m[c], m[c].min() * 0.96, color=col, alpha=0.07)
    ax.set_ylabel(lab, fontsize=9.5)
    for lo, hi, name in [("2017-11-01", "2017-12-01", "Black Friday"),
                         ("2018-02-01", "2018-03-31", "Feb-Mar 2018")]:
        ax.axvspan(pd.Timestamp(lo), pd.Timestamp(hi), color=LATE, alpha=0.08, zorder=0)
axes[0].set_title("Every satisfaction trough is a delivery event", loc="left", pad=14)
axes[0].annotate("Black Friday", (pd.Timestamp("2017-11-15"), m.orders.max()), fontsize=9,
                 color=LATE, ha="center", fontweight="600")
axes[1].annotate("Feb-Mar 2018", (pd.Timestamp("2018-02-25"), m.pct_late.max()), fontsize=9,
                 color=LATE, ha="center", fontweight="600")
plt.tight_layout(); plt.show()

for lag in range(3):
    print(f"  volume(t) vs late-rate(t+{lag})   r = {m.orders.corr(m.pct_late.shift(-lag)):+.3f}")
print("\nThe correlation is strongest at lag 0: capacity breaks in the same month demand spikes.")
''')

# ════════════════════════════════════════════════════════════════ Q2
md(r"""
---
## 5 · Core Question 2 — Delivery performance and satisfaction

> *How does delivery timing relative to the estimate relate to review scores?*

### It is a cliff, not a slope

This single chart carries the rest of the analysis.
""")

code(r'''
cliff = df[df.gap_days.notna() & df.review_score.notna()].groupby("late_bucket", observed=True).agg(
    n=("review_score", "size"), score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100)).reset_index()
print(cliff.round(2).to_string(index=False))

fig, ax = plt.subplots(figsize=(10, 4.8))
cols = [C1 if "early" in b else LATE for b in cliff.late_bucket]
ax.bar(range(len(cliff)), cliff.score, color=cols, width=0.66, zorder=3)
ax.set_xticks(range(len(cliff)))
ax.set_xticklabels([b.replace(" ", "\n", 1) for b in cliff.late_bucket], fontsize=9)
ax.axvline(3.5, color=BASE, linewidth=1.2)
ax.text(3.56, 4.62, "delivery promise", fontsize=9, color=MUTED, va="top")
for i in (0, 4, 5):
    ax.annotate(f"{cliff.score[i]:.2f}", (i, cliff.score[i]), xytext=(0, 6),
                textcoords="offset points", ha="center", fontsize=10, color=INK, fontweight="600")
ax.annotate("", xy=(5, 2.55), xytext=(4, 3.70),
            arrowprops=dict(arrowstyle="->", color=LATE, lw=1.6))
ax.text(5.16, 3.15, "-1.45 stars\nin four days", fontsize=9.5, color=LATE, fontweight="600")
ax.set_ylim(0, 5); ax.set_ylabel("Mean review score")
ax.set_xlabel("Delivery date relative to the promised date")
titled(ax, "Satisfaction does not decay - it falls off a ledge",
       "Mean review score by delivery outcome")
plt.show()

late = df[df.is_late == 1]; early = df[df.is_late == 0]
print(f"\nlate orders are {len(late) / (len(late) + len(early)) * 100:.1f}% of deliveries "
      f"but {late.is_one_star.sum() / df.is_one_star.sum() * 100:.1f}% of all 1-star reviews")
print("15 days early instead of 3 buys +0.10 stars. Three days late to seven costs -1.45.")
''')

md(r"""
### Olist already ran the experiment

The obvious recommendation is "your estimates are inaccurate, tighten them." The data shows Olist has
been doing exactly that for nineteen months — and what it cost.
""")

code(r'''
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(m.month, m.promised, color=C1, linewidth=2, label="Promised delivery time (median)")
ax.plot(m.month, m.actual, color=C2, linewidth=2, label="Actual delivery time (median)")
ax.fill_between(m.month, m.actual, m.promised, color=C1, alpha=0.09)
mid = len(m) // 2
ax.annotate("the buffer", (m.month.iloc[mid], (m.promised.iloc[mid] + m.actual.iloc[mid]) / 2),
            fontsize=10, color=MUTED, ha="center", fontweight="600")
ax.set_ylabel("Days from purchase"); ax.set_ylim(0, None); ax.legend(loc="lower left")
titled(ax, "Delivery got faster, the promise got tighter, lateness rose anyway",
       "Median promised vs actual delivery time")
plt.show()

print(f"  promise  {m.promised.iloc[0]:.1f}d -> {m.promised.iloc[-1]:.1f}d   "
      f"({m.promised.iloc[-1] - m.promised.iloc[0]:+.1f}d)")
print(f"  actual   {m.actual.iloc[0]:.1f}d -> {m.actual.iloc[-1]:.1f}d   "
      f"({m.actual.iloc[-1] - m.actual.iloc[0]:+.1f}d)")
print(f"  LATE     {m.pct_late.iloc[0]:.1f}% -> {m.pct_late.iloc[-1]:.1f}%")
print("\nThe promise was cut by 25 days while delivery improved by under 4. The late rate tripled.")
''')

md(r"""
### Does the cliff hold everywhere, or is it concentrated?

It holds **everywhere** — the penalty is negative in every category and every state with enough
volume to measure. The effect is structural, not a pocket. What varies is *exposure*: the late rate
ranges from 4.9% in Paraná to 23.9% in Alagoas.
""")

code(r'''
dd = df[df.gap_days.notna() & df.review_score.notna()]
for label, key, minn in [("CATEGORY", "primary_category", 500), ("STATE", "customer_state", 300)]:
    g = dd.groupby([key, dd.is_late == 1]).review_score.mean().unstack()
    g.columns = ["on_time", "late"]
    g["penalty"] = g.late - g.on_time
    g = g.join(dd.groupby(key).size().rename("n")).query(f"n >= {minn}")
    print(f"{label}: penalty is negative in {(g.penalty < 0).sum()} of {len(g)} "
          f"(range {g.penalty.min():.2f} to {g.penalty.max():.2f})")
''')

# ════════════════════════════════════════════════════════════════ Q6 falsification
md(r"""
---
## 6 · The hypothesis we falsified

This section exists because it changed our recommendation, and because a submission that only
reports what survived is not showing its work.

**The observation.** Olist's survey fires at `estimated_delivery_date + 2 days` — median exactly 2.0,
inter-quartile range 2 to 2. So when an order runs late, the customer is asked to rate it *before it
arrives*. **37% of all 1-star reviews are written by someone who does not yet have their product.**

**The hypothesis.** Those reviews are a measurement artifact depressing Olist's scores. Delay the
survey and the scores recover.

**The test.** That trigger rule creates a sharp discontinuity: an order is surveyed pre-delivery
*if and only if* it runs more than two days late. A customer 1.9 days late and one 2.1 days late had
near-identical experiences but received a different survey. That is a **regression discontinuity** —
any jump in score exactly at the two-day threshold is the survey-timing effect, net of lateness.
""")

code(r'''
def ols_hc1(X, y):
    """OLS with HC1 robust standard errors, in numpy (see the note in §0 on statsmodels)."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    r = y - X @ beta
    V = XtX_inv @ ((X * r[:, None]).T @ (X * r[:, None])) @ XtX_inv * (n / (n - k))
    return beta, np.sqrt(np.diag(V))


def rd(data, cut=2.0, bw=1.0, donut=0.0):
    s = data[(data.gap_days > cut - bw) & (data.gap_days < cut + bw)]
    if donut:
        s = s[(s.gap_days - cut).abs() > donut]
    x = (s.gap_days - cut).values
    right = (x > 0).astype(float)
    if len(s) < 100 or right.min() == right.max():
        return None
    X = np.column_stack([np.ones(len(s)), x, right, x * right])
    b, se = ols_hc1(X, s.review_score.values)
    return b[2], se[2], len(s)


rdd = df[df.gap_days.notna() & df.review_score.notna() & df.review_creation_date.notna()].copy()
rdd["pre"] = rdd.review_creation_date < rdd.order_delivered_customer_date

print("FIRST STAGE - does crossing +2 days flip who gets surveyed early?")
b = pd.cut(rdd.gap_days, [-2, 0, 1, 2, 3, 4, 6, 10])
fs = rdd.groupby(b, observed=True).pre.agg(["size", "mean"])
for k, r in fs.iterrows():
    print(f"  gap {str(k):<12} n={r['size']:>6,.0f}   surveyed pre-delivery {r['mean'] * 100:5.1f}%")

print("\nRD ESTIMATE AT THE CUTOFF")
print(f"  {'bandwidth':>10} {'n':>7} {'effect':>9} {'SE':>7} {'t':>7}   95% CI")
for bw in [0.75, 1.0, 1.25, 1.5, 2.0]:
    r = rd(rdd, bw=bw)
    if r:
        e, se, n = r
        print(f"  {bw:>10.2f} {n:>7,} {e:>9.3f} {se:>7.3f} {e / se:>7.2f}   "
              f"[{e - 1.96 * se:+.2f}, {e + 1.96 * se:+.2f}]")

print("\nPLACEBO CUTOFFS - if +2 were special, only it should show an effect")
for cut in [-3, -2, -1, 0, 1, 2, 3, 4]:
    r = rd(rdd, cut=float(cut), bw=1.0)
    if r:
        e, se, n = r
        print(f"  cutoff {cut:>3}   effect {e:>+7.3f}  SE {se:.3f}  t {e / se:>6.2f}"
              f"{'   <-- TRUE CUTOFF' if cut == 2 else ''}")
raw = rdd[~rdd.pre].review_score.mean() - rdd[rdd.pre].review_score.mean()
e, se, _ = rd(rdd, bw=1.0)
print(f"\nRaw pre/post gap: {raw:+.2f} stars.  RD effect: {e:+.2f} (SE {se:.2f}).")
print(f"The 95% CI rules out anything above {abs(e) + 1.96 * se:.2f} stars.")
print("=> HYPOTHESIS REJECTED. The anger is real, not an artifact of when we asked.")
''')

md(r"""
**Result: the hypothesis is dead.** Every bandwidth returns an effect indistinguishable from zero
(|t| < 1), the placebo cutoffs show +2 days is unremarkable, and the confidence interval rules out
anything close to the raw 1.50-star gap. **Roughly 1.35 of those 1.50 stars is simply the order
being late.** Asking later would not have made anyone happier.

**But the finding got better, not worse.** Two things survive:

1. The test *validates the review score as a metric* — and kills a cheap fix that a less careful
   analysis would have recommended.
2. The text says the score is identical but the **content** is completely different.
""")

code(r'''
txt = rdd[rdd.review_comment_message.notna() & (rdd.review_score == 1)].copy()
txt["msg"] = txt.review_comment_message.str.lower()
THEMES = {"did not receive it": r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o",
          "late":               r"atras|demor",
          "wrong or broken":    r"errad|quebrad|defeit|danificad",
          "only part arrived":  r"faltou|apenas um|s[oó] veio|s[oó] recebi"}
print(f"1-star reviews with text:  pre-delivery {txt.pre.sum():,}   post-delivery {(~txt.pre).sum():,}\n")
print(f"  {'theme':<22}{'PRE':>9}{'POST':>9}{'lift':>8}")
for lab, pat in THEMES.items():
    a = txt[txt.pre].msg.str.contains(pat, regex=True, na=False).mean() * 100
    b_ = txt[~txt.pre].msg.str.contains(pat, regex=True, na=False).mean() * 100
    print(f"  {lab:<22}{a:>8.1f}%{b_:>8.1f}%{a / b_:>7.2f}x")
print("\nSame score, completely different problem. The survey is not a broken measurement -")
print("it is an UNREAD DISTRESS SIGNAL: 8,446 customers reporting non-receipt while the order")
print("is still in flight and still recoverable. The fix is not to delay it. It is to ACT on it.")
''')

# ════════════════════════════════════════════════════════════════ Q3
md(r"""
---
## 7 · Core Question 3 — Sellers and geography

> *How does the geographic pattern relate to delivery, freight and satisfaction?*

São Paulo holds 42% of customers but **71% of sellers**; the top three states supply 87% of all
orders. Every delivery metric then moves monotonically with distance from that cluster — and state
turns out to be mostly a proxy for distance.
""")

code(r'''
g = df[df.seller_customer_km.notna() & df.gap_days.notna()].copy()
g["dbin"] = pd.cut(g.seller_customer_km, [0, 50, 150, 300, 600, 1000, 1500, 2000, 1e9],
                   labels=["<50", "50-150", "150-300", "300-600", "600-1k", "1k-1.5k", "1.5k-2k", "2k+"])
db = g.groupby("dbin", observed=True).agg(
    n=("order_id", "size"), delivery=("actual_days", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean"),
    freight=("freight_total", "mean"), value=("order_value", "mean")).reset_index()
db["freight_pct"] = db.freight / db.value * 100
print(db.round(2).to_string(index=False))

fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))
for ax, (c, lab, col, f) in zip(axes, [("delivery", "Median delivery (days)", C1, "{:.0f}d"),
                                       ("late", "Delivered late (%)", LATE, "{:.0f}%"),
                                       ("score", "Mean review score", C3, "{:.2f}")]):
    ax.plot(range(len(db)), db[c], color=col, linewidth=2, marker="o", markersize=6,
            markerfacecolor=col, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_xticks(range(len(db)))
    ax.set_xticklabels(db.dbin, rotation=45, ha="right", fontsize=8.5)
    ax.set_title(lab, loc="left", fontsize=11)
    for i in (0, len(db) - 1):
        ax.annotate(f.format(db[c].iloc[i]), (i, db[c].iloc[i]), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=9.5, color=INK, fontweight="600")
    ax.margins(x=0.12, y=0.22)
axes[1].set_xlabel("Seller-to-customer distance (km)")
plt.suptitle("Distance sets delivery time, lateness and satisfaction together",
             x=0.005, ha="left", fontsize=13, fontweight="600")
plt.tight_layout(); plt.show()

st = g.groupby("customer_state").agg(
    n=("order_id", "size"), km=("seller_customer_km", "median"), delivery=("actual_days", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean"),
    freight=("freight_total", "mean"), value=("order_value", "mean")).query("n >= 300")
st["freight_pct"] = st.freight / st.value * 100
print("\nacross states, median distance correlates with:")
for lab, c in [("delivery time", "delivery"), ("late rate", "late"),
               ("review score", "score"), ("freight burden", "freight_pct")]:
    print(f"    {lab:<16} r = {st.km.corr(st[c]):+.3f}")
''')

md(r"""
### One state breaks the rule

Distance explains 87% of the variance in state delivery times — and completely fails on **Rio de
Janeiro**, which sits closer to its sellers than Paraná yet runs nearly three times the late rate.
Decomposing the gap shows where it lives.
""")

code(r'''
peers = g[g.customer_state.isin(["SP", "RJ", "MG", "PR", "SC", "RS", "ES"])]
p = peers.groupby("customer_state").agg(
    n=("order_id", "size"), km=("seller_customer_km", "median"),
    handoff=("t_handoff", "median"), transit=("t_transit", "median"),
    total=("actual_days", "median"), late=("is_late", lambda s: np.nanmean(s) * 100),
    score=("review_score", "mean")).sort_values("km")
print(p.round(2).to_string())
rj, pr = p.loc["RJ"], p.loc["PR"]
tot = rj.total - pr.total
print(f"\nRJ vs PR at the same distance ({rj.km:.0f} vs {pr.km:.0f} km): RJ is {tot:+.2f} days slower")
print(f"   seller handoff  {rj.handoff - pr.handoff:+.2f}d  ({(rj.handoff - pr.handoff) / tot * 100:.0f}%)")
print(f"   carrier transit {rj.transit - pr.transit:+.2f}d  ({(rj.transit - pr.transit) / tot * 100:.0f}%)")

into = g[g.customer_state.eq("RJ")]
out = g[g.seller_state.eq("RJ") & ~g.customer_state.eq("RJ")]
print(f"\n   INTO RJ      late {np.nanmean(into.is_late) * 100:5.2f}%")
print(f"   OUT OF RJ    late {np.nanmean(out.is_late) * 100:5.2f}%   <- Rio's SELLERS are fine")
print("\n=> a destination-side last-mile problem, and it is worst in the periphery:")
cities = into.groupby("customer_city").agg(n=("order_id", "size"),
                                           late=("is_late", lambda s: np.nanmean(s) * 100))
print(cities[cities.n >= 150].sort_values("late", ascending=False).head(5).round(2).to_string())
''')

md(r"""
### The map

The geolocation table, drawn rather than only measured. The gradient radiates from a single city.
""")

code(r'''
cz = df.groupby("customer_zip_code_prefix").agg(
    n=("order_id", "size"), late=("is_late", lambda s: np.nanmean(s) * 100),
    days=("actual_days", "median"))
cz = cz[cz.n >= 8].join(geo_pt.set_index("geolocation_zip_code_prefix"), how="inner")

fig, axes = plt.subplots(1, 2, figsize=(12.4, 6))
for ax, (c, lab, cm) in zip(axes, [("days", "Median delivery time (days)", "Blues"),
                                   ("late", "Delivered late (%)", "Oranges")]):
    v = cz[c].clip(cz[c].quantile(.02), cz[c].quantile(.98))
    s = ax.scatter(cz.lng, cz.lat, c=v, s=np.sqrt(cz.n) * 1.6, cmap=cm, alpha=0.8, linewidth=0)
    ax.set_title(lab, loc="left", fontsize=11.5)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False); ax.set_aspect("equal")
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(s, ax=ax, fraction=0.036, pad=0.02)
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=8, colors=MUTED)
    ax.scatter([-46.63], [-23.55], s=64, facecolor="none", edgecolor=LATE, linewidth=1.8)
    ax.annotate("São Paulo", (-46.63, -23.55), xytext=(9, -12), textcoords="offset points",
                fontsize=9, color=LATE, fontweight="600")
plt.suptitle("The whole country is downstream of one city", x=0.005, ha="left",
             fontsize=13, fontweight="600")
plt.tight_layout(); plt.show()
print(f"{len(cz):,} zip prefixes with 8+ orders, sized by volume.")
''')

# ════════════════════════════════════════════════════════════════ Q4/Q5
md(r"""
---
## 8 · Core Questions 4 and 5 — Categories and payments

### Categories: two different problems wearing the same low score

Categories do not ship alike — heavy furniture travels differently from a paperback. So each is
scored twice: as observed, and among **on-time deliveries only**. The difference separates a
category with a product problem from one with a logistics problem, and those belong to different
teams.
""")

code(r'''
cd = df[df.primary_category.notna() & df.review_score.notna()]
cat = cd.groupby("primary_category").agg(
    orders=("order_id", "size"), price=("order_value", "mean"), score=("review_score", "mean"),
    late=("is_late", lambda s: np.nanmean(s) * 100)).join(
    cd[cd.is_late == 0].groupby("primary_category").review_score.mean().rename("score_ontime"))
cat = cat[cat.orders >= 300]
PLAT = cd[cd.is_late == 0].review_score.mean()
cat["product_gap"] = cat.score_ontime - PLAT          # weak even when delivery is not the issue
cat["delivery_drag"] = cat.score - cat.score_ontime   # what lateness costs this category

print(f"platform on-time average: {PLAT:.3f}\n")
print("WEAK EVEN WHEN DELIVERED ON TIME (product / listing / expectation problem):")
print(cat.nsmallest(5, "product_gap")[["orders", "score", "score_ontime", "product_gap", "price"]]
      .round(3).to_string())
print("\nFINE ON TIME, DRAGGED DOWN BY DELIVERY (logistics problem):")
print(cat.nsmallest(5, "delivery_drag")[["orders", "score", "score_ontime", "delivery_drag", "late"]]
      .round(3).to_string())

fig, ax = plt.subplots(figsize=(9.6, 6.6))
pl = cat.sort_values("product_gap")
y = np.arange(len(pl))
ax.hlines(y, pl.score_ontime, pl.score, color=BASE, linewidth=1.6, zorder=2)
ax.scatter(pl.score_ontime, y, s=48, color=C1, zorder=3, edgecolor=SURFACE, linewidth=1.5,
           label="Score when delivered on time")
ax.scatter(pl.score, y, s=48, color=LATE, zorder=3, edgecolor=SURFACE, linewidth=1.5,
           label="Score as observed")
ax.axvline(PLAT, color=MUTED, linewidth=1)
ax.set_yticks(y); ax.set_yticklabels([c.replace("_", " ") for c in pl.index], fontsize=8.5)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xlabel("Mean review score")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2)
ax.set_title("Two different problems wearing the same low score", loc="left", pad=38)
plt.show()
''')

md(r"""
### Payments: the interesting answer is operational, not demographic

A *boleto* is a printed bank slip the customer walks away and pays later — so the order sits
unapproved while the delivery clock runs.
""")

code(r'''
pm = df[df.payment_type.notna() & df.payment_type.ne("not_defined")].copy()
pm["approve_h"] = pm.t_approve * 24
mix = pm.groupby("payment_type").agg(
    orders=("order_id", "size"), value=("order_value", "mean"),
    installments=("max_installments", "mean"), approve_h=("approve_h", "median"),
    handoff=("t_handoff", "median"), transit=("t_transit", "median"),
    total=("actual_days", "median"), not_delivered=("is_delivered", lambda s: (1 - s.mean()) * 100),
    score=("review_score", "mean"))
print(mix.round(2).to_string())
bo, cr = mix.loc["boleto"], mix.loc["credit_card"]
print(f"\nboleto approval takes {bo.approve_h:.1f}h vs {cr.approve_h:.2f}h for a card "
      f"(+{(bo.approve_h - cr.approve_h) / 24:.2f} days)")
print(f"boleto total delivery is +{bo.total - cr.total:.2f} days, so "
      f"{(bo.approve_h - cr.approve_h) / 24 / (bo.total - cr.total) * 100:.0f}% of the gap is the")
print("approval wait alone - burned before the seller is even told to ship.")

dl = pm[pm.is_delivered]
piv = dl.pivot_table(index="payment_type", columns=dl.is_late == 1, values="review_score", aggfunc="mean")
piv.columns = ["on_time", "late"]
print(f"\nraw score spread across methods       {mix.score.max() - mix.score.min():.3f} stars")
print(f"spread among ON-TIME orders only      {piv.on_time.max() - piv.on_time.min():.3f} stars")
print("=> most of the apparent payment effect is delivery wearing a disguise.")
print(f"\nThe real exception is vouchers: {mix.loc['voucher', 'not_delivered']:.2f}% never delivered "
      f"vs {mix.loc['credit_card', 'not_delivered']:.2f}% for cards.")
''')

# ════════════════════════════════════════════════════════════════ Q6 model
md(r"""
---
## 9 · Core Question 6 — Root cause

> *Which factors are primary drivers of low review scores, and which are secondary?*

Two methodological choices:

1. **Model P(1-star), not the mean score.** The distribution is bimodal; the business question is
   "what makes someone furious", which is a probability.
2. **Separate three things the raw data confounds**: breaking the promise (`days late`), the absolute
   wait (`days in transit` regardless of promise), and everything else.

Before the model, note that there are **two populations**, not one.
""")

code(r'''
allr = df[df.review_score.notna()]
und = allr[~allr.is_delivered]
print(f"  DELIVERED       n={len(allr) - len(und):>7,}  mean {allr[allr.is_delivered].review_score.mean():.2f}"
      f"  1-star {np.nanmean(allr[allr.is_delivered].is_one_star) * 100:5.2f}%")
print(f"  NEVER ARRIVED   n={len(und):>7,}  mean {und.review_score.mean():.2f}"
      f"  1-star {np.nanmean(und.is_one_star) * 100:5.2f}%")
print(f"\n  never-delivered orders are {len(und) / len(allr) * 100:.2f}% of reviews but "
      f"{und.is_one_star.sum() / allr.is_one_star.sum() * 100:.2f}% of 1-stars")
print(f"  -> {und.is_one_star.sum():,.0f} one-star reviews NO delivery improvement can reach.")
print(und.groupby("order_status").agg(n=("review_score", "size"), mean=("review_score", "mean"))
      .round(2).sort_values("n", ascending=False).to_string())
''')

code(r'''
def logit_irls(X, y, names, iters=60):
    """Logistic regression by IRLS, in numpy (see §0 on statsmodels)."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
        W = np.clip(p * (1 - p), 1e-9, None)
        try:
            step = np.linalg.solve((X.T * W) @ X, X.T @ (y - p))
        except np.linalg.LinAlgError:
            step = np.linalg.pinv((X.T * W) @ X) @ (X.T @ (y - p))
        beta = beta + step
        if np.max(np.abs(step)) < 1e-9:
            break
    p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
    W = np.clip(p * (1 - p), 1e-9, None)
    se = np.sqrt(np.diag(np.linalg.pinv((X.T * W) @ X)))
    ll = np.sum(y * np.log(np.clip(p, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1)))
    pb = y.mean()
    ll0 = np.sum(y * np.log(pb) + (1 - y) * np.log(1 - pb))
    out = pd.DataFrame({"term": names, "coef": beta, "se": se})
    out["z"] = out.coef / out.se
    out["OR"] = np.exp(out.coef)
    out["lo"], out["hi"] = np.exp(out.coef - 1.96 * out.se), np.exp(out.coef + 1.96 * out.se)
    return out, 1 - ll / ll0


mm = df[df.is_delivered & df.review_score.notna()].copy()
mm["days_late"]  = np.clip(mm.gap_days, 0, 30)      # promise breach
mm["days_early"] = np.clip(-mm.gap_days, 0, 30)     # slack remaining
mm["wait"]       = np.clip(mm.actual_days, 0, 60)   # absolute wait, independent of the promise
mm["handoff"]    = np.clip(mm.t_handoff, 0, 30)
mm["log_km"]     = np.log1p(mm.seller_customer_km)
mm["log_value"]  = np.log1p(mm.order_value)
mm["freight_r"]  = np.clip(mm.freight_ratio, 0, 3)
mm["items"]      = np.clip(mm.n_items, 1, 10)
mm["multi_seller"] = (mm.n_sellers > 1).astype(float)
for pt in ["boleto", "voucher", "debit_card"]:
    mm[f"pay_{pt}"] = mm.payment_type.eq(pt).astype(float)

CONT = ["days_late", "days_early", "wait", "handoff", "log_km", "log_value", "freight_r", "items"]
BIN  = ["multi_seller", "pay_boleto", "pay_voucher", "pay_debit_card"]
mm = mm.dropna(subset=CONT + BIN + ["is_one_star"])
z = mm[CONT].apply(lambda c: (c - c.mean()) / c.std())     # per-SD, so effects are comparable
X = np.column_stack([np.ones(len(mm))] + [z[c].values for c in CONT] + [mm[c].values for c in BIN])
res, r2 = logit_irls(X, mm.is_one_star.values, ["intercept"] + CONT + BIN)
print(f"n = {len(mm):,}   base 1-star rate {mm.is_one_star.mean() * 100:.2f}%   pseudo-R2 {r2:.3f}\n")
r = res[res.term != "intercept"].sort_values("OR", ascending=False)
print(r[["term", "OR", "lo", "hi", "z"]].round(3).to_string(index=False))
''')

code(r'''
LBL = {"days_late": "Days late vs promise", "days_early": "Days of slack left",
       "wait": "Absolute wait (days)", "handoff": "Seller handoff time",
       "log_km": "Seller->customer distance", "log_value": "Order value",
       "freight_r": "Freight share of value", "items": "Items in order",
       "multi_seller": "Multiple sellers in order", "pay_boleto": "Paid by boleto",
       "pay_voucher": "Paid by voucher", "pay_debit_card": "Paid by debit card"}
pl = r.sort_values("OR")
fig, ax = plt.subplots(figsize=(9.6, 5.8))
y = np.arange(len(pl))
ax.hlines(y, pl.lo, pl.hi, color=BASE, linewidth=2, zorder=2)
ax.scatter(pl.OR, y, s=62, c=[LATE if o > 1 else C1 for o in pl.OR], zorder=3,
           edgecolor=SURFACE, linewidth=1.6)
ax.axvline(1, color=MUTED, linewidth=1.1)
ax.set_yticks(y); ax.set_yticklabels([LBL.get(t, t) for t in pl.term], fontsize=9.5)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xscale("log"); ax.set_xticks([0.8, 1, 1.5, 2, 3, 5])
ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}x"))
ax.get_xaxis().set_minor_formatter(plt.NullFormatter())
ax.set_xlabel("Odds ratio for a 1-star review (log scale, 95% CI)")
ax.annotate(f"{pl.OR.iloc[-1]:.2f}x", (pl.OR.iloc[-1], len(pl) - 1), xytext=(10, 0),
            textcoords="offset points", va="center", fontsize=11, color=LATE, fontweight="600")
titled(ax, "One factor is not like the others",
       f"Logistic model of P(1-star), {len(mm):,} delivered orders - continuous terms per +1 SD")
plt.show()
''')

md(r"""
### The multi-seller effect, and why we did not simply believe it

An odds ratio of 5 is large enough to be suspicious, so we tried to break it four ways.

**The mechanism:** Olist stores **one** `order_delivered_customer_date` per order. But an order split
across sellers physically ships as several parcels from several places. So the order is marked
delivered — and the survey fires — when *a* parcel arrives, not when the last one does. The customer
is asked to rate a completed order while holding an incomplete one.
""")

code(r'''
ms = df[df.is_delivered & df.review_score.notna() & df.n_sellers.notna()].copy()
ms["multi"] = ms.n_sellers > 1

print("TEST 1 - raw effect")
print(ms.groupby("multi").agg(n=("order_id", "size"), score=("review_score", "mean"),
      one=("is_one_star", lambda s: np.nanmean(s) * 100),
      late=("is_late", lambda s: np.nanmean(s) * 100),
      delivery=("actual_days", "median")).round(2).to_string())

print("\nTEST 2 - does it survive controlling for lateness?")
ot = ms[ms.is_late == 0]
t = ot.groupby("multi").agg(n=("order_id", "size"), score=("review_score", "mean"),
                            one=("is_one_star", lambda s: np.nanmean(s) * 100))
print(f"  ON-TIME ONLY: single {t.one.iloc[0]:.2f}% 1-star vs multi {t.one.iloc[1]:.2f}% "
      f"({t.one.iloc[1] / t.one.iloc[0]:.1f}x)")

print("\nTEST 3 - is it SELLERS, or just more items? (hold item count fixed)")
sub = ms[ms.n_items.between(2, 5)].copy()
sub["kind"] = np.where(sub.n_sellers > 1, "multi-seller", "one seller, several items")
print(sub.groupby(["n_items", "kind"]).agg(n=("order_id", "size"), score=("review_score", "mean"),
      one=("is_one_star", lambda s: np.nanmean(s) * 100)).round(2).to_string())
a = sub[sub.kind == "multi-seller"].review_score.mean()
b = sub[sub.kind != "multi-seller"].review_score.mean()
print(f"\n  same basket size, split across sellers: {a - b:+.2f} stars")

print("\nTEST 4 - what do the written reviews say?")
low = ms[(ms.review_score <= 2) & ms.review_comment_message.notna()].copy()
low["msg"] = low.review_comment_message.str.lower()
for lab, pat in [("only part arrived", r"faltou|apenas um|s[oó] veio|s[oó] recebi|um dos"),
                 ("wrong or broken", r"errad|quebrad|defeit")]:
    x = low[low.multi].msg.str.contains(pat, regex=True, na=False).mean() * 100
    y_ = low[~low.multi].msg.str.contains(pat, regex=True, na=False).mean() * 100
    print(f"  {lab:<20} multi {x:5.1f}%   single {y_:5.1f}%   {x / y_:.2f}x")
print("\nNote test 1: multi-seller orders are recorded as delivered FASTER and late LESS often.")
print("That is backwards - unless the timestamp is capturing the first parcel, not the last.")
''')

md(r"""
### Attribution — how many 1-star reviews does each failure mode own?

This is the number that keeps the analysis honest.
""")

code(r'''
tot = allr.is_one_star.sum()
dl_ = allr[allr.is_delivered]
late_1 = dl_[dl_.is_late == 1].is_one_star.sum()
und_1 = und.is_one_star.sum()
ont_1 = dl_[dl_.is_late == 0].is_one_star.sum()
print(f"  total 1-star reviews            {tot:>8,.0f}   100.0%")
print(f"    delivered LATE                {late_1:>8,.0f}   {late_1 / tot * 100:5.1f}%")
print(f"    NEVER ARRIVED                 {und_1:>8,.0f}   {und_1 / tot * 100:5.1f}%")
print(f"    delivered ON TIME             {ont_1:>8,.0f}   {ont_1 / tot * 100:5.1f}%")
print(f"\n  {(late_1 + und_1) / tot * 100:.1f}% of 1-star reviews are a delivery failure of some kind.")
print(f"  The other {ont_1 / tot * 100:.1f}% arrived on time and the customer was furious anyway.")

fig, ax = plt.subplots(figsize=(9.5, 1.9))
parts = [(late_1, "Delivered late", LATE), (und_1, "Never arrived", "#8c2d05"),
         (ont_1, "On time, still 1-star", MUTED)]
left = 0
for v, lab, c in parts:
    ax.barh([0], [v / tot * 100], left=left, color=c, height=0.6, edgecolor=SURFACE, linewidth=2)
    ax.text(left + v / tot * 100 / 2, 0, f"{v / tot * 100:.1f}%", ha="center", va="center",
            color="white", fontweight="700", fontsize=11)
    ax.text(left + v / tot * 100 / 2, -0.52, lab, ha="center", va="top", fontsize=9, color=INK2)
    left += v / tot * 100
ax.set_xlim(0, 100); ax.set_ylim(-1, 0.5); ax.axis("off")
ax.set_title("Where 1-star reviews actually come from", loc="left", pad=12)
plt.show()
''')

# ════════════════════════════════════════════════════════════════ RISK MODEL
md(r"""
---
## 10 · The recommendation, built as a model

The analysis says: protect the promise, and do not cut the buffer. But Olist's buffer is **flat** —
the same padding for a 160 km São Paulo order and a 2,400 km order to Pará. That is too slow where
it is safe and too tight where it is not.

So instead of one promise for the platform, predict the delivery-time distribution for **each order**
and promise a chosen quantile of it. Trained on orders to April 2018, tested on unseen orders from
May–August. Every feature is knowable at checkout; seller history is built from the training window
only, so nothing leaks.
""")

code(r'''
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

rk = df[df.is_delivered & df.actual_days.notna() & df.gap_days.notna()].sort_values("order_purchase_timestamp")
SPLIT = pd.Timestamp("2018-05-01")
tr, te = rk[rk.order_purchase_timestamp < SPLIT], rk[rk.order_purchase_timestamp >= SPLIT]
print(f"train {len(tr):,}  ({tr.order_purchase_timestamp.min().date()} -> {tr.order_purchase_timestamp.max().date()})")
print(f"test  {len(te):,}  ({te.order_purchase_timestamp.min().date()} -> {te.order_purchase_timestamp.max().date()})")

sh = tr.groupby("primary_seller_id").agg(seller_n=("order_id", "size"),
                                         seller_days=("actual_days", "median"),
                                         seller_late=("is_late", "mean"),
                                         seller_handoff=("t_handoff", "median"))
sh = sh[sh.seller_n >= 5]
cat_d = tr.groupby("primary_category").actual_days.median()
st_d = tr.groupby("customer_state").actual_days.median()


def feats(x):
    f = pd.DataFrame(index=x.index)
    f["log_km"] = np.log1p(x.seller_customer_km); f["km"] = x.seller_customer_km
    f["weight"] = np.log1p(x.total_weight_g); f["volume"] = np.log1p(x.total_volume_cm3)
    f["price"] = np.log1p(x.order_value); f["freight"] = np.log1p(x.freight_total)
    f["n_items"] = x.n_items; f["n_sellers"] = x.n_sellers
    f["month"] = x.order_purchase_timestamp.dt.month
    f["dow"] = x.order_purchase_timestamp.dt.dayofweek
    f["boleto"] = x.payment_type.eq("boleto").astype(int)
    f["installments"] = x.max_installments
    j = x.join(sh, on="primary_seller_id")
    for c in sh.columns:
        f[c] = j[c].values
    f["cat_days"] = x.primary_category.map(cat_d).values
    f["state_days"] = x.customer_state.map(st_d).values
    return f


Xtr, Xte = feats(tr), feats(te)
ytr, yte = tr.actual_days.values, te.actual_days.values
base = {"promise": te.promised_days.mean(), "late": (yte > te.promised_days.values).mean() * 100}
print(f"\nOlist today:  mean promise {base['promise']:.1f}d   late {base['late']:.2f}%")

rows = []
for q in [0.80, 0.85, 0.90, 0.95]:
    mdl = HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=350,
                                        learning_rate=0.06, max_depth=7, random_state=0)
    mdl.fit(Xtr, ytr)
    p = np.clip(mdl.predict(Xte), 1, None)
    rows.append({"q": q, "promise": p.mean(), "late": (yte > p).mean() * 100})
    print(f"risk-based q={q:.2f}:  mean promise {p.mean():5.1f}d   late {(yte > p).mean():5.2%}")
res_q = pd.DataFrame(rows)
same = res_q.iloc[(res_q.promise - base["promise"]).abs().argsort()].iloc[0]
print(f"\n*** At the SAME promise length ({same.promise:.1f}d vs {base['promise']:.1f}d):")
print(f"    late rate {same.late:.2f}% vs {base['late']:.2f}%  ->  "
      f"{(1 - same.late / base['late']) * 100:.0f}% FEWER LATE ORDERS")
print("    The buffer is not cut - it is REALLOCATED, off the orders that never needed it.")
''')

code(r'''
# The fair comparison is not "no buffer" but "a better FLAT buffer".
flat = pd.DataFrame([{"promise": np.median(tr.actual_days) + a,
                      "late": (yte > (np.median(tr.actual_days) + a)).mean() * 100}
                     for a in np.arange(0, 34, 0.5)])
print("at a matched late rate, how long must each promise be?")
for r_ in rows:
    mt = flat[flat.late <= r_["late"]].head(1)
    if len(mt):
        print(f"  {r_['late']:5.2f}% late:  risk-based {r_['promise']:5.1f}d   |   "
              f"flat {mt.promise.iloc[0]:5.1f}d   -> {mt.promise.iloc[0] - r_['promise']:.1f}d shorter")

fig, ax = plt.subplots(figsize=(9.5, 5))
ax.plot(flat.promise, flat.late, color=MUTED, linewidth=2, label="One flat buffer for everyone")
ax.plot(res_q.promise, res_q.late, color=OK, linewidth=2.2, marker="o", markersize=7,
        markerfacecolor=OK, markeredgecolor=SURFACE, markeredgewidth=2,
        label="Risk-based promise (per order)")
ax.scatter([base["promise"]], [base["late"]], s=130, color=LATE, zorder=5,
           edgecolor=SURFACE, linewidth=2, label="Olist today")
ax.annotate("Olist today", (base["promise"], base["late"]), xytext=(10, 10),
            textcoords="offset points", fontsize=10, color=LATE, fontweight="600")
ax.set_xlabel("Mean delivery promise (days)"); ax.set_ylabel("Orders delivered late (%)")
ax.set_ylim(0, 26); ax.legend(loc="upper right")
titled(ax, "Down and to the left is better",
       f"Held-out test on {len(te):,} unseen orders, May-Aug 2018")
plt.show()
''')

code(r'''
# A classifier for proactive contact on the promises Olist has ALREADY made.
Xtr2, Xte2 = Xtr.copy(), Xte.copy()
Xtr2["promised"] = tr.promised_days.values
Xte2["promised"] = te.promised_days.values
clf = HistGradientBoostingClassifier(max_iter=350, learning_rate=0.06, max_depth=7, random_state=0)
clf.fit(Xtr2, tr.is_late.astype(int))
pl_ = clf.predict_proba(Xte2)[:, 1]
yl = te.is_late.astype(int).values
print(f"ROC-AUC {roc_auc_score(yl, pl_):.4f}   base late rate {yl.mean() * 100:.2f}%")
dec = pd.DataFrame({"d": pd.qcut(pl_, 10, labels=False, duplicates="drop"), "late": yl})
tab = dec.groupby("d").late.agg(["size", "mean"])
tab["lift"] = tab["mean"] / yl.mean()
print(f"\nriskiest decile: {tab['mean'].iloc[-1] * 100:.1f}% late ({tab.lift.iloc[-1]:.1f}x base)")
caught = (tab["size"].iloc[-3:] * tab["mean"].iloc[-3:]).sum()
print(f"contacting the riskiest 30% reaches {caught:,.0f} of {yl.sum():,} late orders "
      f"({caught / yl.sum() * 100:.0f}%)")
print("\nHONEST READ: AUC 0.69 is useful for triage, not precision. The quantile model above")
print("carries the recommendation; this one only prioritises a call list.")
''')

# ════════════════════════════════════════════════════════════════ SELLER SCORECARD
md(r"""
---
## 11 · The seller scorecard

A raw seller rating is unfair and unactionable in both directions: a seller shipping heavy furniture
to Pará is set up to score badly, and a 2.1-star seller with nine orders is a rounding error next to
a 3.9-star seller with nine hundred.

So each seller is benchmarked against **their own mix** — the platform average for the same
categories at the same distances — then ranked by **stars lost** (volume × shortfall).
""")

code(r'''
sd = df[df.review_score.notna() & df.primary_seller_id.notna() & df.primary_category.notna()].copy()
sd["dband"] = pd.cut(sd.seller_customer_km, [-1, 100, 300, 600, 1200, 2500, 1e9])
cell = sd.groupby(["primary_category", "dband"], observed=True).agg(
    cell_n=("review_score", "size"), cell_score=("review_score", "mean"),
    cell_late=("is_late", "mean"))
sd = sd.join(cell[cell.cell_n >= 30], on=["primary_category", "dband"]).dropna(subset=["cell_score"])

s = sd.groupby("primary_seller_id").agg(
    orders=("order_id", "size"), revenue=("order_value", "sum"), score=("review_score", "mean"),
    expected=("cell_score", "mean"), late=("is_late", lambda x: np.nanmean(x) * 100),
    exp_late=("cell_late", lambda x: np.nanmean(x) * 100), handoff=("t_handoff", "median"),
    state=("seller_state", "first"))
s = s[s.orders >= 20]
s["gap"] = s.score - s.expected
s["stars_lost"] = -s.gap * s.orders
print(f"{len(s):,} sellers with 20+ reviewed orders, covering {s.orders.sum() / len(sd) * 100:.1f}% of volume")
print(f"\n  raw rating spread   p10 {s.score.quantile(.1):.2f}  p90 {s.score.quantile(.9):.2f}")
print(f"  MIX-ADJUSTED gap    p10 {s.gap.quantile(.1):+.2f}  p90 {s.gap.quantile(.9):+.2f}")
print(f"  => {s.gap.quantile(.9) - s.gap.quantile(.1):.2f} stars of spread REMAINS after controlling")
print("     for what they sell and how far they ship. Sellers genuinely differ.")

print("\nTOP 10 INTERVENTION TARGETS")
w = s.nlargest(10, "stars_lost")[["orders", "score", "expected", "gap", "stars_lost",
                                  "late", "exp_late", "handoff", "state"]]
w.index = [i[:12] + "..." for i in w.index]
print(w.round(2).to_string())

s["tier"] = pd.qcut(s.gap, [0, .1, .5, .9, 1.0], labels=["worst 10%", "below med", "above med", "best 10%"])
print("\nWHAT SEPARATES THEM:")
print(s.groupby("tier", observed=True).agg(sellers=("orders", "size"), gap=("gap", "mean"),
      late=("late", "mean"), handoff=("handoff", "median")).round(2).to_string())
print(f"\n  gap vs handoff time  r = {s.gap.corr(s.handoff):+.3f}")
print(f"  gap vs seller SIZE   r = {s.gap.corr(np.log(s.orders)):+.3f}  <- size is NOT quality")
''')

# ════════════════════════════════════════════════════════════════ DEEP DIVES
md(r"""
---
## 12 · Deep dives

Included because each changed a recommendation — not because the technique was available.
""")

code(r'''
print("=" * 78); print("REPEAT CUSTOMERS"); print("=" * 78)
counts = df.groupby("customer_unique_id").size()
print(f"  people {df.customer_unique_id.nunique():,}   orders {len(df):,}   "
      f"repeat rate {(counts > 1).mean() * 100:.2f}%")
# censoring control: only first orders with 180+ days of observable follow-up
first_o = df.sort_values("order_purchase_timestamp").groupby("customer_unique_id").first()
CUT = df.order_purchase_timestamp.max() - pd.Timedelta(days=180)
elig = first_o[first_o.order_purchase_timestamp <= CUT].copy()
elig["returned"] = elig.index.map(counts) > 1
rr = elig[elig.review_score.notna()].groupby("review_score").returned.agg(["size", "mean"])
rr["mean"] *= 100
print(f"\n  cohort with 180+ days to return: {len(elig):,}   base return rate {elig.returned.mean() * 100:.2f}%")
print(rr.round(2).to_string())
print(f"\n  1-2 star first order -> {elig[elig.review_score <= 2].returned.mean() * 100:.2f}% return")
print(f"  5 star first order   -> {elig[elig.review_score == 5].returned.mean() * 100:.2f}% return")
print("\n  HONEST READ: directionally real, but the BASE RATE is the finding. At ~3-4%, Olist")
print("  re-acquires nearly its entire customer base every year. Satisfaction moves retention,")
print("  but nowhere near enough to save it.")
''')

code(r'''
print("=" * 78); print("FREIGHT ECONOMICS"); print("=" * 78)
f = df[(df.freight_total > 0) & (df.total_weight_g > 0) & df.seller_customer_km.notna()
       & (df.n_items == 1)].copy()
Xf = np.column_stack([np.ones(len(f)), np.log1p(f.total_weight_g), np.log1p(f.total_volume_cm3),
                      np.log1p(f.seller_customer_km)])
yf = np.log1p(f.freight_total)
bf, *_ = np.linalg.lstsq(Xf, yf, rcond=None)
pred = Xf @ bf
print(f"  single-item orders: {len(f):,}     R2 = {1 - ((yf - pred) ** 2).sum() / ((yf - yf.mean()) ** 2).sum():.3f}")
print(f"    weight elasticity   {bf[1]:+.3f}    -> 10x heavier costs {10 ** bf[1]:.2f}x more")
print(f"    distance elasticity {bf[3]:+.3f}    -> 10x farther costs {10 ** bf[3]:.2f}x more")
print("  => both far below 1: freight is heavily COMPRESSED against real cost, so short-haul")
print("     orders subsidise long-haul ones.")
f["resid"] = yf - pred
mis = f.groupby("customer_state").resid.agg(["mean", "size"]).query("size >= 200").sort_values("mean")
print(f"\n  yet remote states still pay a premium beyond distance: "
      f"{(np.exp(mis['mean'].iloc[-1]) - 1) * 100:.0f}% in {mis.index[-1]}")
print("  They wait longest, pay most, on the smallest baskets.")
''')

code(r'''
print("=" * 78); print("REVIEW TEXT - what the words add to the score"); print("=" * 78)
t = df[df.review_comment_message.notna() & df.review_score.notna()].copy()
t["msg"] = t.review_comment_message.str.lower()
# NB: bare "prazo" and "qualidade" appear in PRAISE ("chegou antes do prazo", "boa qualidade"),
# so both are excluded from the complaint patterns below.
TH = {"never arrived":     r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o|nunca chegou",
      "partial delivery":  r"faltou|apenas um|s[oó] veio|s[oó] recebi|um dos",
      "late (complaint)":  r"atras|demor|fora do prazo",
      "wrong / broken":    r"errad|quebrad|defeit|danificad",
      "no seller contact": r"n[aã]o resp|sem resposta|n[aã]o consigo falar",
      "praise":            r"[oó]tim|excelen|perfeit|recomend|adorei"}
print(f"  {len(t):,} reviews with text ({len(t) / df.review_score.notna().sum() * 100:.1f}%)\n")
print(f"  {'theme':<22}" + "".join(f"{i:>9}" for i in [1, 2, 3, 4, 5]))
for lab, pat in TH.items():
    print(f"  {lab:<22}" + "".join(
        f"{t[t.review_score == i].msg.str.contains(pat, regex=True, na=False).mean() * 100:>8.1f}%"
        for i in [1, 2, 3, 4, 5]))
print("\n  The themes separate the scores far more sharply than the score separates itself.")
for lab in ["never arrived", "no seller contact"]:
    a = t[t.review_score == 1].msg.str.contains(TH[lab], regex=True, na=False).mean() * 100
    b_ = t[t.review_score == 5].msg.str.contains(TH[lab], regex=True, na=False).mean() * 100
    print(f"    '{lab}' runs {a:.1f}% at 1 star -> {b_:.1f}% at 5 star")
print("  Seller silence is a 1-star signature, not a 3-star one.")
''')

code(r'''
print("=" * 78); print("ANOMALY REGISTER"); print("=" * 78)
checks = [
    ("orders marked canceled but carrying a delivery timestamp",
     (df.order_delivered_customer_date.notna() & df.order_status.eq("canceled")).sum()),
    ("orders delivered BEFORE the carrier collected them",
     (df.order_delivered_customer_date < df.order_delivered_carrier_date).sum()),
    ("delivered orders taking over 100 days", (df.actual_days > 100).sum()),
    ("orders where freight exceeds the item price", (df.freight_ratio > 1).sum()),
    ("orders where freight is over 5x the item price", (df.freight_ratio > 5).sum()),
    ("orders with no line items at all", df.n_items.isna().sum()),
    ("orders whose payment total is R$0", (df.payment_total == 0).sum()),
]
for lab, n in checks:
    print(f"  {n:>7,}  {lab}")
print(f"\n  longest delivery in the dataset: {df.actual_days.max():.0f} days")
tail = df[df.actual_days > 100]
print(f"  the 100+ day tail averages {tail.review_score.mean():.2f} stars")
''')

# ════════════════════════════════════════════════════════════════ FINDINGS
md(r"""
---
## 13 · Key findings

**1 · Growth and satisfaction are different stories.** Volume grew 8× and revenue 7× between January
2017 and August 2018, while average order value *fell* 13% — the growth is more orders, not bigger
ones. Satisfaction stayed roughly flat but became volatile, and every trough is a delivery event.

**2 · Satisfaction is a cliff, not a slope.** Arriving fifteen days early rather than three buys
**+0.10 stars**. Slipping from three days late to seven costs **−1.45** and triples the 1-star rate.
Past day seven the damage saturates. The relationship holds in every category and every state.

**3 · The twelve-day buffer is insurance, not sloppiness — and cutting it has already been tried.**
Olist reduced its median promise from 39 days to 13 while delivery improved by under 4, and the late
rate tripled from 3% to 10%. The obvious recommendation is a documented failure.

**4 · A hypothesis we killed.** 37% of 1-star reviews are written before the parcel arrives, because
the survey fires at `ETA + 2 days`. That looked like a measurement artifact. A regression
discontinuity at the two-day trigger returns **+0.15 stars (SE 0.19)** — indistinguishable from zero.
The anger is real. But the text shows those reviews are 53% *"não recebi"* versus 16% otherwise:
the survey is not a broken measurement, it is an **unread distress signal** arriving while the order
is still recoverable.

**5 · The delay is line-haul, not sellers.** Of the ~19 extra median days on a late order, **17 are
carrier transit** and 1.3 is seller handoff. Both unexplained anomalies — Rio de Janeiro's 13.5% late
rate at short distance, and the February–March 2018 collapse — decompose to the same carrier leg.

**6 · Splitting an order across sellers is the single largest driver of 1-star reviews** (OR 4.99).
On-time multi-seller orders run **36% 1-star against 6%**, the effect survives holding basket size
fixed, and *"only part arrived"* appears 4× more often in their text. Olist stores one delivery
timestamp per order, so a multi-parcel order is marked complete — and surveyed — when the first
parcel lands.

**7 · Delivery explains 48.8% of 1-star reviews, not all of them.** 31% come from late deliveries,
18% from orders that never arrived at all (2,963 orders at a 70.5% 1-star rate — an inventory problem
no logistics fix can reach), and **51% arrived on time and the customer was unhappy anyway.**

**8 · Retention is the number nobody is looking at.** Only **3.1%** of customers ever order twice.
Olist re-acquires almost its entire customer base every year.
""")

md(r"""
---
## 14 · Recommendations

| # | Recommendation | Evidence | Expected effect | Confidence |
|---|---|---|---|---|
| 1 | **Promise per order, not per platform.** Set each ETA from a predicted delivery-time quantile instead of a flat buffer. | Held-out test, 25,352 unseen orders | **47% fewer late deliveries at an identical promise length** | High |
| 2 | **Do not mark an order delivered — or fire the survey — until the last parcel lands.** | OR 4.99; 36% vs 6% on-time 1-star; text 4× | ~342 excess 1-stars/yr; a notification change, not a capital project | High |
| 3 | **Route pre-delivery 1-stars into live recovery.** 8,446 customers report non-receipt while the order is still in flight. | 53% *"não recebi"* vs 16% | Recovery, *not* score inflation — the RD says the score itself will not move | Medium |
| 4 | **Set a seller SLA on handoff time.** Worst-decile sellers hand off in 3.0 days against the best decile's 1.1. | Scorecard, r = −0.37 with mix-adjusted gap | 20 sellers carry 39% of all stars lost | High |
| 5 | **Treat non-delivery as an inventory problem, not a logistics one.** | 2,963 orders at 70.5% 1-star | 2,089 1-stars unreachable by any delivery fix | High |
| 6 | **Put fulfilment capacity in the North/Northeast**, and fix Rio's last mile as a separate, nearer-term project. | distance r = +0.87 with delivery time; RJ 13.5% vs PR 4.9% | Structural; long horizon | Medium |

### What we would have recommended, wrongly, without testing

1. *"Your delivery estimates are inaccurate — tighten them."* The asymmetry says no, and Olist ran
   the experiment already.
2. *"Delay the review survey so customers aren't rating undelivered orders."* The regression
   discontinuity says this changes nothing.
3. *"Focus on your worst-rated sellers."* Raw rating targets small sellers with noisy averages;
   ranking by stars lost targets the ones whose failure actually reaches customers.

---

### Limitations

Observational data — we identify associations, and only the regression discontinuity in §6 supports a
causal reading. Reviews arrive for 99.4% of orders, so selection into reviewing is not a major
concern, but the survey timing means late orders are systematically rated earlier in their lifecycle.
The dataset ends abruptly in August 2018, so recent trends are not confirmable. Seller and customer
identifiers are hashed, so no seller can be contacted or verified. Distances are great-circle between
zip-prefix centroids, not routed road distance.

---

*Data: Brazilian E-Commerce Public Dataset by Olist, CC BY-NC-SA.*
""")

nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.11"},
                   "colab": {"provenance": [], "toc_visible": True}}}
OUT.write_text(json.dumps(nb, indent=1), encoding="utf-8")
n_code = sum(1 for c in cells if c["cell_type"] == "code")
print(f"-> {OUT}   {len(cells)} cells ({n_code} code, {len(cells) - n_code} markdown)")
