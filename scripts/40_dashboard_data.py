"""Export everything the dashboard needs as one JSON payload embedded in the page.

The promise simulator needs a fine grid of risk quantiles rather than the four used in the
analysis, so the model is refit across 0.60-0.99 to give the slider something smooth to move over.
"""
import pandas as pd, numpy as np, pathlib, sys, json, warnings
from sklearn.ensemble import HistGradientBoostingRegressor
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
OUT = ROOT / "dashboard"
OUT.mkdir(exist_ok=True)

d = df[df.is_delivered & df.actual_days.notna() & df.gap_days.notna()].copy()
d["purchase"] = pd.to_datetime(d.order_purchase_timestamp)
d = d.sort_values("purchase")
SPLIT = pd.Timestamp("2018-05-01")
tr, te = d[d.purchase < SPLIT], d[d.purchase >= SPLIT]

sh = tr.groupby("primary_seller_id").agg(
    seller_n=("order_id", "size"), seller_med_days=("actual_days", "median"),
    seller_late_rate=("is_late", "mean"), seller_med_handoff=("t_handoff", "median"))
sh = sh[sh.seller_n >= 5]
cat_days = tr.groupby("primary_category").actual_days.median().rename("cat_med_days")
state_days = tr.groupby("customer_state").actual_days.median().rename("state_med_days")


def build(x):
    f = pd.DataFrame(index=x.index)
    f["km"] = x.seller_customer_km; f["log_km"] = np.log1p(x.seller_customer_km)
    f["weight"] = np.log1p(x.total_weight_g); f["volume"] = np.log1p(x.total_volume_cm3)
    f["price"] = np.log1p(x.order_value); f["freight"] = np.log1p(x.freight_total)
    f["n_items"] = x.n_items; f["n_sellers"] = x.n_sellers
    f["month"] = x.purchase.dt.month; f["dow"] = x.purchase.dt.dayofweek
    f["is_boleto"] = x.payment_type.eq("boleto").astype(int)
    f["installments"] = x.max_installments
    j = x.join(sh, on="primary_seller_id")
    for c in sh.columns:
        f[c] = j[c].values
    f["cat_med_days"] = x.join(cat_days, on="primary_category").cat_med_days.values
    f["state_med_days"] = x.join(state_days, on="customer_state").state_med_days.values
    return f


Xtr, Xte = build(tr), build(te)
ytr, yte = tr.actual_days.values, te.actual_days.values

# ── the score-vs-gap curve, for projecting satisfaction under a new promise ──
dd = d[d.review_score.notna()].copy()
dd["gbin"] = np.clip(np.round(dd.gap_days), -45, 45)
cur = dd.groupby("gbin").agg(n=("review_score", "size"), s=("review_score", "mean"))
cur = cur[cur.n >= 30]
gx, gy = cur.index.values.astype(float), cur.s.values

print("fitting the promise frontier...")
frontier = []
for q in np.round(np.arange(0.60, 0.996, 0.01), 3):
    m = HistGradientBoostingRegressor(loss="quantile", quantile=float(q), max_iter=350,
                                      learning_rate=0.06, max_depth=7, random_state=0)
    m.fit(Xtr, ytr)
    p = np.clip(m.predict(Xte), 1, None)
    new_gap = yte - p
    frontier.append({"q": float(q), "promise": float(p.mean()),
                     "late": float((yte > p).mean() * 100),
                     "score": float(np.interp(np.clip(new_gap, gx.min(), gx.max()), gx, gy).mean())})
    print(f"  q={q:.2f}  promise {p.mean():5.1f}d  late {(yte > p).mean() * 100:5.2f}%")

# flat-buffer comparator: one promise length for everyone
flat = []
for add in np.arange(0, 41, 0.5):
    pr = np.median(tr.actual_days) + add
    new_gap = yte - pr
    flat.append({"promise": float(pr), "late": float((yte > pr).mean() * 100),
                 "score": float(np.interp(np.clip(new_gap, gx.min(), gx.max()), gx, gy).mean())})

today = {"promise": float(te.promised_days.mean()),
         "late": float((yte > te.promised_days.values).mean() * 100),
         "score": float(te.review_score.mean())}

# ── seller queue ─────────────────────────────────────────────────────────────
sc = pd.read_parquet(ROOT / "data" / "processed" / "seller_scorecard.parquet")
sc = sc.sort_values("stars_lost", ascending=False).head(40).reset_index()
sellers = [{"id": r.primary_seller_id[:10], "orders": int(r.orders), "revenue": round(r.revenue),
            "score": round(r.score, 2), "expected": round(r.exp_score, 2),
            "gap": round(r.score_gap, 2), "lost": round(r.stars_lost),
            "late": round(r.late, 1), "expLate": round(r.exp_late, 1),
            "handoff": round(r.handoff, 1), "state": r.state, "cat": r.top_cat}
           for r in sc.itertuples()]

# ── supporting series ────────────────────────────────────────────────────────
w = d[d.in_trend_window].copy()
w["m"] = w.purchase.dt.to_period("M").astype(str)
mon = w.groupby("m").agg(orders=("order_id", "size"), late=("is_late", lambda s: np.nanmean(s) * 100),
                         score=("review_score", "mean"), transit=("t_transit", "median"),
                         handoff=("t_handoff", "median"), promised=("promised_days", "median"),
                         actual=("actual_days", "median")).reset_index()

cliff = dd.groupby("late_bucket", observed=True).agg(
    n=("review_score", "size"), score=("review_score", "mean"),
    one=("is_one_star", lambda s: np.nanmean(s) * 100)).reset_index()

payload = {
    "today": today,
    "frontier": frontier,
    "flat": flat,
    "sellers": sellers,
    "monthly": mon.round(3).to_dict("records"),
    "cliff": [{"bucket": str(r.late_bucket), "n": int(r.n), "score": round(r.score, 3),
               "one": round(r.one, 2)} for r in cliff.itertuples()],
    "stats": {
        "orders": int(len(df)), "sellers": int(df.primary_seller_id.nunique()),
        "customers": int(df.customer_unique_id.nunique()),
        "meanScore": round(float(df.review_score.mean()), 3),
        "lateShare": round(float(np.nanmean(d.is_late) * 100), 2),
        "oneStarFromLate": 31.0, "oneStarFromNever": 17.7, "oneStarFromOnTime": 51.2,
        "repeatRate": 3.12, "multiSellerOR": 4.99,
        "nTrain": int(len(tr)), "nTest": int(len(te)),
    },
}
(OUT / "data.json").write_text(json.dumps(payload), encoding="utf-8")
print(f"\n-> {OUT / 'data.json'}  ({(OUT / 'data.json').stat().st_size / 1024:.0f} KB)")
