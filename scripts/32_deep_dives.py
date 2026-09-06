"""
OPTIONAL DEEP DIVES - repeat customers, freight economics, review text, anomalies.

Each of these is included because it changes a recommendation, not because the technique is
available. The repeat-purchase section is the one that converts the whole analysis from a
satisfaction story into a revenue story.
"""
import pandas as pd, numpy as np, pathlib, sys, warnings
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _style as S

warnings.filterwarnings("ignore")
S.apply()
ROOT = pathlib.Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
FIG = ROOT / "figures"


def hdr(t): print("\n" + "=" * 90 + "\n" + t + "\n" + "=" * 90)


# ══════════════════════════════════════════════════ 1. REPEAT CUSTOMERS
hdr("1. REPEAT CUSTOMERS - does a bad first order cost Olist the second one?")
d = df.copy()
d["purchase"] = pd.to_datetime(d.order_purchase_timestamp)
first = d.sort_values("purchase").groupby("customer_unique_id").first()
n_people, n_orders = d.customer_unique_id.nunique(), len(d)
counts = d.groupby("customer_unique_id").size()
print(f"  people {n_people:,}   orders {n_orders:,}   repeat rate {(counts > 1).mean() * 100:.2f}% of people")
print(f"  orders from repeat buyers: {counts[counts > 1].sum():,} ({counts[counts > 1].sum() / n_orders * 100:.2f}%)")

# censoring control: only first orders with >=180 days of observable follow-up
CUTOFF = d.purchase.max() - pd.Timedelta(days=180)
elig = first[first.purchase <= CUTOFF].copy()
elig["returned"] = elig.index.map(counts) > 1
print(f"\n  restricting to first orders placed on or before {CUTOFF.date()} so every customer has")
print(f"  at least 180 days to come back: {len(elig):,} customers")
print(f"  overall return rate in that cohort: {elig.returned.mean() * 100:.2f}%\n")
r = elig[elig.review_score.notna()].groupby("review_score").agg(
    customers=("returned", "size"), return_rate=("returned", lambda s: s.mean() * 100))
r["index_vs_5star"] = r.return_rate / r.return_rate.loc[5] * 100
print(r.round(2).to_string())
lo = elig[(elig.review_score <= 2) & elig.review_score.notna()].returned.mean() * 100
hi = elig[elig.review_score == 5].returned.mean() * 100
print(f"\n  first order rated 1-2 stars -> {lo:.2f}% return")
print(f"  first order rated 5 stars   -> {hi:.2f}% return")
print(f"  relative difference: {(lo / hi - 1) * 100:+.1f}%")
print("\n  CAVEAT: with a 3.0% base return rate the absolute gap is small and the cohort is thin.")
print("  The honest read is that Olist has almost no repeat business from ANY cohort - the")
print("  retention problem dwarfs the satisfaction differential inside it.")

ltv = d.groupby("customer_unique_id").agg(orders=("order_id", "size"), spend=("order_value", "sum"))
rep, one = ltv[ltv.orders > 1], ltv[ltv.orders == 1]
print(f"\n  lifetime spend: repeat R${rep.spend.mean():.2f} (n={len(rep):,})  vs  "
      f"one-time R${one.spend.mean():.2f} (n={len(one):,})   -> {rep.spend.mean() / one.spend.mean():.2f}x")
print(f"  repeat buyers are {len(rep) / len(ltv) * 100:.2f}% of customers but "
      f"{rep.spend.sum() / ltv.spend.sum() * 100:.2f}% of revenue")

# ══════════════════════════════════════════════════ 2. FREIGHT ECONOMICS
hdr("2. FREIGHT vs PRODUCT CHARACTERISTICS - what is Olist actually charging for?")
f = df[df.freight_total.notna() & df.total_weight_g.notna() & df.seller_customer_km.notna()].copy()
f = f[(f.freight_total > 0) & (f.total_weight_g > 0) & (f.n_items == 1)]
f["log_w"] = np.log1p(f.total_weight_g); f["log_v"] = np.log1p(f.total_volume_cm3)
f["log_km"] = np.log1p(f.seller_customer_km); f["log_f"] = np.log1p(f.freight_total)
print(f"  single-item orders analysed: {len(f):,}")
print("\n  correlation with freight charged:")
for lab, c in [("weight (log)", "log_w"), ("volume (log)", "log_v"), ("distance (log)", "log_km"),
               ("order value (log)", "price")]:
    col = np.log1p(f.order_value) if c == "price" else f[c]
    print(f"    {lab:<20} r = {np.corrcoef(col, f.log_f)[0, 1]:+.3f}")

X = np.column_stack([np.ones(len(f)), f.log_w, f.log_v, f.log_km])
beta, *_ = np.linalg.lstsq(X, f.log_f, rcond=None)
pred = X @ beta
ss_res, ss_tot = ((f.log_f - pred) ** 2).sum(), ((f.log_f - f.log_f.mean()) ** 2).sum()
print(f"\n  log-log model  log(freight) ~ log(weight) + log(volume) + log(distance)")
print(f"    weight elasticity   {beta[1]:+.3f}   (a 10% heavier parcel costs {beta[1] * 10:+.2f}% more)")
print(f"    volume elasticity   {beta[2]:+.3f}")
print(f"    distance elasticity {beta[3]:+.3f}   (a 10% longer trip costs {beta[3] * 10:+.2f}% more)")
print(f"    R2 = {1 - ss_res / ss_tot:.3f}")
print(f"\n  => BOTH elasticities are far below 1: a 10x longer trip raises freight only "
      f"{10 ** beta[3]:.2f}x,")
print(f"     and a 10x heavier parcel only {10 ** beta[1]:.2f}x. Freight is heavily compressed against")
print("     real cost, so long-haul orders are cross-subsidised by short-haul ones.")

f["resid"] = f.log_f - pred
mis = f.groupby("customer_state").resid.agg(["mean", "size"]).query("size >= 200").sort_values("mean")
print(f"\n  states paying LESS than weight/volume/distance predict:")
print(mis.head(4).round(3).to_string())
print(f"  states paying MORE than weight/volume/distance predict:")
print(mis.tail(4).round(3).to_string())
print(f"\n  => remote northern states pay a premium of up to {(np.exp(mis['mean'].iloc[-1]) - 1) * 100:.0f}% "
      f"BEYOND what their distance alone explains -")
print("     probably genuine last-mile cost, but it compounds their disadvantage: they wait the")
print("     longest AND pay the most, on the smallest order values.")

# ══════════════════════════════════════════════════ 3. REVIEW TEXT
hdr("3. REVIEW TEXT - what the words add to the score")
t = df[df.review_comment_message.notna() & df.review_score.notna()].copy()
t["msg"] = t.review_comment_message.str.lower()
print(f"  reviews with text: {len(t):,} of {df.review_score.notna().sum():,} "
      f"({len(t) / df.review_score.notna().sum() * 100:.1f}%)")
print(f"  comment rate by score: " + "  ".join(
    f"{k}star {v * 100:.0f}%" for k, v in
    df.groupby("review_score").review_comment_message.apply(lambda s: s.notna().mean()).items()))
t["length"] = t.msg.str.len()
print(f"\n  median comment length by score:")
print(t.groupby("review_score").length.median().round(0).to_string())
THEMES = {
    "never arrived":     r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o|nunca chegou",
    "partial delivery":  r"faltou|falta |apenas um|s[oó] veio|s[oó] recebi|um dos",
    "late (complaint)":  r"atras|demor|fora do prazo|n[aã]o cumpr",
    "wrong / broken":    r"errad|quebrad|defeit|danificad|avariad",
    # NB: bare "qualidade" is useless here - it appears in "boa qualidade" (good quality) just as
    # often as in "pessima qualidade", which flattens the row across all five scores.
    "poor quality":      r"p[eé]ssim|ruim|horr[ií]vel|fraco|m[aá] qualidade|baixa qualidade",
    "no seller contact": r"n[aã]o resp|sem resposta|contato|n[aã]o consigo falar",
    "praise":            r"[oó]tim|excelen|perfeit|recomend|adorei|super r[aá]pid",
}
print(f"\n  {'theme':<22}" + "".join(f"{s:>9}" for s in [1, 2, 3, 4, 5]))
for lab, pat in THEMES.items():
    row = "".join(f"{t[t.review_score == s].msg.str.contains(pat, regex=True, na=False).mean() * 100:>8.1f}%"
                  for s in [1, 2, 3, 4, 5])
    print(f"  {lab:<22}{row}")
five_neg = t[(t.review_score == 5) & t.msg.str.contains(THEMES["late (complaint)"], regex=True, na=False)]
print(f"\n  {len(five_neg):,} FIVE-star reviews still mention a delay "
      f"({len(five_neg) / (t.review_score == 5).sum() * 100:.1f}% of 5-star comments)")
print("  => a small group forgives the delay and rates 5 anyway - invisible in the score alone.")
print("\n  the themes separate the scores far more sharply than the score separates itself:")
print("  'never arrived' runs 29.5% -> 1.4% across 1 to 5 stars, and 'no seller contact'")
print("  5.6% -> 0.2%. Silence from the seller is a 1-star signature, not a 3-star one.")

# ══════════════════════════════════════════════════ 4. ANOMALIES
hdr("4. ANOMALIES WORTH FLAGGING SEPARATELY")
a = []
a.append(("orders marked canceled but with a delivery timestamp",
          int((df.order_delivered_customer_date.notna() & df.order_status.eq("canceled")).sum())))
a.append(("orders delivered BEFORE the carrier collected them", int(df.timestamp_anomaly.sum())))
a.append(("delivered orders taking over 100 days", int((df.actual_days > 100).sum())))
a.append(("orders where freight exceeds the item price", int((df.freight_ratio > 1).sum())))
a.append(("orders where freight is over 5x the item price", int((df.freight_ratio > 5).sum())))
a.append(("products with zero or missing weight", int(df.total_weight_g.fillna(0).le(0).sum())))
a.append(("orders with no line items at all", int(df.n_items.isna().sum())))
a.append(("payment records typed 'not_defined' (R$0)", int(df.has_undefined_payment.fillna(False).sum())))
a.append(("orders whose payment total is R$0", int((df.payment_total == 0).sum())))
a.append(("reviews answered before the survey was created", int(
    (pd.to_datetime(df.review_answer_timestamp) < pd.to_datetime(df.review_creation_date)).sum())))
for lab, n in a:
    print(f"  {n:>7,}  {lab}")

print("\n  the extreme delivery tail:")
tail = df[df.actual_days > 100][["order_id", "order_status", "actual_days", "gap_days",
                                 "customer_state", "review_score", "primary_category"]]
print(f"    n={len(tail)}   max {df.actual_days.max():.0f} days   "
      f"mean review score {tail.review_score.mean():.2f}")
print(f"    states: {', '.join(f'{k}={v}' for k, v in tail.customer_state.value_counts().head(5).items())}")

print("\n  freight outliers (freight > 5x item price):")
fo = df[df.freight_ratio > 5][["order_value", "freight_total", "freight_ratio", "total_weight_g",
                               "seller_customer_km", "review_score"]]
print(f"    n={len(fo)}   median item price R${fo.order_value.median():.2f}   "
      f"median freight R${fo.freight_total.median():.2f}   "
      f"median weight {fo.total_weight_g.median():.0f}g")
print(f"    their mean review score {fo.review_score.mean():.2f} vs platform {df.review_score.mean():.2f}")

# ── FIG: retention ───────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.2, 4.8))
rr = r.return_rate
ax.bar(rr.index, rr.values, color=[S.CRITICAL if i <= 2 else S.C1 for i in rr.index],
       width=0.62, zorder=3)
for i, v in rr.items():
    ax.annotate(f"{v:.1f}%", (i, v), xytext=(0, 6), textcoords="offset points", ha="center",
                fontsize=10, color=S.INK, fontweight="600")
ax.set_xlabel("Review score on the customer's FIRST order")
ax.set_ylabel("Returned to buy again (%)")
ax.set_title("Almost nobody comes back — least of all the people you disappointed",
             loc="left", pad=40)
ax.text(0, 1.05, f"{len(elig):,} first-time customers with at least 180 days of observable follow-up",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "The base rate is the headline: a ~3% return rate means Olist re-acquires almost its entire "
            "customer base every year. Satisfaction moves it, but not nearly enough to save it.")
S.save(fig, "q9_retention", FIG)
