"""Export the analyses the dashboard was still missing, so its charts can be drawn natively
in its own visual language rather than pasted in as matplotlib PNGs.

Adds: a coarse map grid, seller->customer distance bands, P(1-star) driver odds ratios,
the multi-seller 2x2, state peers for the Rio anomaly, review-text themes, and price bands.
"""
import pandas as pd, numpy as np, pathlib, json, warnings
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
OUT = ROOT / "dashboard" / "data.json"
P = json.loads(OUT.read_text(encoding="utf-8"))
d = df[df.review_score.notna()]

# ── map: aggregate zip prefixes onto a 0.35-degree grid so it renders as a field, not 4k dots
geo = pd.read_csv(RAW / "geolocation.csv")
inside = (geo.geolocation_lat.between(-33.75, 5.28) & geo.geolocation_lng.between(-73.99, -34.79))
gpt = geo[inside].groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].mean()
cz = df.groupby("customer_zip_code_prefix").agg(
    n=("order_id", "size"), late=("is_late", lambda s: np.nanmean(s) * 100),
    days=("actual_days", "median")).join(gpt, how="inner")
cz = cz[cz.n >= 5]
cz["gy"] = (cz.geolocation_lat / 0.35).round() * 0.35
cz["gx"] = (cz.geolocation_lng / 0.35).round() * 0.35
grid = cz.groupby(["gx", "gy"]).apply(lambda g: pd.Series({
    "n": g.n.sum(),
    "days": np.average(g.days, weights=g.n),
    "late": np.average(g.late.fillna(0), weights=g.n)})).reset_index()
P["map"] = [[round(r.gx, 2), round(r.gy, 2), int(r.n), round(r.days, 1), round(r.late, 1)]
            for r in grid.itertuples()]

# ── distance bands
g = df[df.seller_customer_km.notna() & df.gap_days.notna()].copy()
g["b"] = pd.cut(g.seller_customer_km, [0, 50, 150, 300, 600, 1000, 1500, 2000, 1e9],
                labels=["<50", "50-150", "150-300", "300-600", "600-1k", "1-1.5k", "1.5-2k", "2k+"])
db = g.groupby("b", observed=True).agg(
    n=("order_id", "size"), days=("actual_days", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean"),
    freight=("freight_total", "mean"), value=("order_value", "mean")).reset_index()
P["distance"] = [{"b": str(r.b), "n": int(r.n), "days": round(r.days, 1), "late": round(r.late, 2),
                  "score": round(r.score, 3), "freightPct": round(r.freight / r.value * 100, 1)}
                 for r in db.itertuples()]

# ── driver odds ratios (same model as the notebook, numpy IRLS)
def logit(X, y, it=60):
    X, y = np.asarray(X, float), np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        W = np.clip(p * (1 - p), 1e-9, None)
        b = b + np.linalg.pinv((X.T * W) @ X) @ (X.T @ (y - p))
    p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
    W = np.clip(p * (1 - p), 1e-9, None)
    return b, np.sqrt(np.diag(np.linalg.pinv((X.T * W) @ X)))

m = df[df.is_delivered & df.review_score.notna()].copy()
m["days_late"] = np.clip(m.gap_days, 0, 30); m["days_early"] = np.clip(-m.gap_days, 0, 30)
m["wait"] = np.clip(m.actual_days, 0, 60); m["handoff"] = np.clip(m.t_handoff, 0, 30)
m["log_km"] = np.log1p(m.seller_customer_km); m["log_value"] = np.log1p(m.order_value)
m["freight_r"] = np.clip(m.freight_ratio, 0, 3); m["items"] = np.clip(m.n_items, 1, 10)
m["multi_seller"] = (m.n_sellers > 1).astype(float)
for pt in ["boleto", "voucher", "debit_card"]:
    m["pay_" + pt] = m.payment_type.eq(pt).astype(float)
CONT = ["days_late", "days_early", "wait", "handoff", "log_km", "log_value", "freight_r", "items"]
BIN = ["multi_seller", "pay_boleto", "pay_voucher", "pay_debit_card"]
m = m.dropna(subset=CONT + BIN + ["is_one_star"])
z = m[CONT].apply(lambda c: (c - c.mean()) / c.std())
X = np.column_stack([np.ones(len(m))] + [z[c].values for c in CONT] + [m[c].values for c in BIN])
b, se = logit(X, m.is_one_star.values)
LBL = {"days_late": "Days late vs promise", "days_early": "Days of slack left",
       "wait": "Absolute wait", "handoff": "Seller handoff time", "log_km": "Seller→customer distance",
       "log_value": "Order value", "freight_r": "Freight share of value", "items": "Items in order",
       "multi_seller": "Multiple sellers in order", "pay_boleto": "Paid by boleto",
       "pay_voucher": "Paid by voucher", "pay_debit_card": "Paid by debit card"}
terms = CONT + BIN
P["drivers"] = sorted([{"k": LBL[t], "or": round(float(np.exp(b[i + 1])), 3),
                        "lo": round(float(np.exp(b[i + 1] - 1.96 * se[i + 1])), 3),
                        "hi": round(float(np.exp(b[i + 1] + 1.96 * se[i + 1])), 3),
                        "z": round(float(b[i + 1] / se[i + 1]), 1)}
                       for i, t in enumerate(terms)], key=lambda x: -x["or"])
P["driverN"] = int(len(m))

# ── multi-seller 2x2
ms = df[df.is_delivered & df.review_score.notna() & df.n_sellers.notna()].copy()
ms["multi"] = ms.n_sellers > 1
cell = []
for late in [0, 1]:
    for multi in [False, True]:
        s = ms[(ms.is_late == late) & (ms.multi == multi)]
        cell.append({"late": bool(late), "multi": bool(multi), "n": int(len(s)),
                     "one": round(float(np.nanmean(s.is_one_star) * 100), 2)})
P["multiSeller"] = cell

# ── state peers (the Rio anomaly)
pk = g[g.customer_state.isin(["SP", "RJ", "MG", "PR", "SC", "RS", "ES", "BA", "CE", "PA", "AL", "MA"])]
st = pk.groupby("customer_state").agg(
    n=("order_id", "size"), km=("seller_customer_km", "median"),
    handoff=("t_handoff", "median"), transit=("t_transit", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean"))
P["states"] = [{"s": i, "n": int(r.n), "km": round(r.km), "handoff": round(r.handoff, 2),
                "transit": round(r.transit, 2), "late": round(r.late, 2), "score": round(r.score, 3)}
               for i, r in st.iterrows()]

# ── review-text themes ("prazo"/"qualidade" excluded: both appear in praise)
t = d[d.review_comment_message.notna()].copy()
t["msg"] = t.review_comment_message.str.lower()
TH = {"Never arrived": r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o|nunca chegou",
      "Only part arrived": r"faltou|apenas um|s[oó] veio|s[oó] recebi|um dos",
      "Late": r"atras|demor|fora do prazo",
      "Wrong or broken": r"errad|quebrad|defeit|danificad",
      "Seller never replied": r"n[aã]o resp|sem resposta|n[aã]o consigo falar",
      "Praise": r"[oó]tim|excelen|perfeit|recomend|adorei"}
P["themes"] = [{"k": k, "v": [round(float(t[t.review_score == s].msg.str.contains(p, regex=True, na=False).mean() * 100), 1)
                              for s in [1, 2, 3, 4, 5]]} for k, p in TH.items()]
P["themeN"] = int(len(t))

# ── price bands
pb = d[d.order_value.notna()].copy()
pb["b"] = pd.qcut(pb.order_value, [0, .2, .4, .6, .8, .95, 1],
                  labels=["cheapest 20%", "20-40%", "40-60%", "60-80%", "80-95%", "top 5%"])
pbg = pb.groupby("b", observed=True).agg(
    one=("is_one_star", lambda s: np.nanmean(s) * 100), fr=("freight_ratio", "median"),
    price=("order_value", "median")).reset_index()
P["price"] = [{"b": str(r.b), "one": round(r.one, 2), "fr": round(r.fr * 100, 1),
               "price": round(r.price)} for r in pbg.itertuples()]

OUT.write_text(json.dumps(P), encoding="utf-8")
print(f"-> {OUT}  {OUT.stat().st_size/1024:.0f} KB")
for k in ["map", "distance", "drivers", "multiSeller", "states", "themes", "price"]:
    print(f"   {k:<12} {len(P[k])} entries")
