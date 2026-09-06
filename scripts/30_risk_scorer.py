"""
THE DELIVERY RISK SCORER  -  turning the Q2 finding into an operating policy.

Q2 established the trade Olist cannot escape: a shorter promise is more competitive, but every day
cut converts on-time orders into late ones, and lateness costs ~2 stars while earliness buys ~0.1.
Today Olist resolves that trade with a FLAT buffer - the same padding for a 160km Sao Paulo order and
a 2,400km order to Para. That is the worst of both worlds: too slow where it is safe, too tight
where it is not.

The fix is to promise per order rather than per platform. Two models:

  A. QUANTILE model - predict the 90th percentile of delivery time for THIS order, and promise that.
     By construction ~10% run late, but the promise is as short as that risk allows, order by order.
  B. CLASSIFIER - P(late) under the promise actually given, for flagging orders that need proactive
     contact before the customer chases them.

Leakage discipline: split by TIME (train on the past, test on the future), and build every
seller-history feature from the training window only.
"""
import pandas as pd, numpy as np, pathlib, sys, warnings, json
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _style as S

warnings.filterwarnings("ignore")
S.apply()
ROOT = pathlib.Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
FIG, OUT = ROOT / "figures", ROOT / "data" / "processed"


def hdr(t): print("\n" + "=" * 88 + "\n" + t + "\n" + "=" * 88)


# ═══════════════════════════════════════════════════════ frame
d = df[df.is_delivered & df.actual_days.notna() & df.gap_days.notna()].copy()
d["purchase"] = pd.to_datetime(d.order_purchase_timestamp)
d = d.sort_values("purchase")
SPLIT = pd.Timestamp("2018-05-01")
tr, te = d[d.purchase < SPLIT], d[d.purchase >= SPLIT]
hdr("SETUP")
print(f"  train : {len(tr):>7,} orders  {tr.purchase.min().date()} -> {tr.purchase.max().date()}")
print(f"  test  : {len(te):>7,} orders  {te.purchase.min().date()} -> {te.purchase.max().date()}")
print(f"  test late rate under Olist's actual promise: {np.nanmean(te.is_late) * 100:.2f}%")
print(f"  test median promise: {te.promised_days.median():.1f}d   actual: {te.actual_days.median():.1f}d")

# ═══════════════════════════════════════════════════════ features (checkout-time only)
# seller history is computed from TRAIN ONLY, then mapped onto both sets.
sh = tr.groupby("primary_seller_id").agg(
    seller_n=("order_id", "size"),
    seller_med_days=("actual_days", "median"),
    seller_late_rate=("is_late", "mean"),
    seller_med_handoff=("t_handoff", "median"))
sh = sh[sh.seller_n >= 5]
cat_days = tr.groupby("primary_category").actual_days.median().rename("cat_med_days")
state_days = tr.groupby("customer_state").actual_days.median().rename("state_med_days")


def build(x):
    f = pd.DataFrame(index=x.index)
    f["km"] = x.seller_customer_km
    f["log_km"] = np.log1p(x.seller_customer_km)
    f["weight"] = np.log1p(x.total_weight_g)
    f["volume"] = np.log1p(x.total_volume_cm3)
    f["price"] = np.log1p(x.order_value)
    f["freight"] = np.log1p(x.freight_total)
    f["n_items"] = x.n_items
    f["n_sellers"] = x.n_sellers
    f["month"] = x.purchase.dt.month
    f["dow"] = x.purchase.dt.dayofweek
    f["is_boleto"] = x.payment_type.eq("boleto").astype(int)
    f["installments"] = x.max_installments
    j = x.join(sh, on="primary_seller_id")
    for c in sh.columns:
        f[c] = j[c].values
    f["cat_med_days"] = x.join(cat_days, on="primary_category").cat_med_days.values
    f["state_med_days"] = x.join(state_days, on="customer_state").state_med_days.values
    return f


Xtr, Xte = build(tr), build(te)
ytr_days, yte_days = tr.actual_days.values, te.actual_days.values
print(f"  features: {Xte.shape[1]}   (all knowable at checkout; seller history from train only)")

# ═══════════════════════════════════════════════════════ A. quantile promise model
hdr("MODEL A - QUANTILE MODEL: promise the 90th percentile of predicted delivery time")
results = []
preds = {}
for q in [0.80, 0.85, 0.90, 0.95]:
    m = HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=350,
                                      learning_rate=0.06, max_depth=7, random_state=0)
    m.fit(Xtr, ytr_days)
    p = np.clip(m.predict(Xte), 1, None)
    preds[q] = p
    # NB: name it "q", not "quantile" - the latter shadows Series.quantile on itertuples/attr access
    results.append({"q": q, "mean_promise_d": p.mean(), "median_promise_d": np.median(p),
                    "late_rate_pct": (yte_days > p).mean() * 100})
res = pd.DataFrame(results)

ACTUAL_PROMISE = te.promised_days.values
baseline = {"mean_promise_d": ACTUAL_PROMISE.mean(), "median_promise_d": np.median(ACTUAL_PROMISE),
            "late_rate_pct": (yte_days > ACTUAL_PROMISE).mean() * 100}
print(f"  Olist today          : mean promise {baseline['mean_promise_d']:5.1f}d   "
      f"late {baseline['late_rate_pct']:5.2f}%")
for r in results:
    print(f"  risk-based q={r['q']:.2f}    : mean promise {r['mean_promise_d']:5.1f}d   "
          f"late {r['late_rate_pct']:5.2f}%   "
          f"({r['mean_promise_d'] - baseline['mean_promise_d']:+.1f}d, "
          f"{r['late_rate_pct'] - baseline['late_rate_pct']:+.2f}pp)")

# Dominance is two-sided: hold the promise fixed and read off lateness, or hold lateness
# fixed and read off the promise. Either one alone understates the gain.
same_len = res.iloc[(res.mean_promise_d - baseline["mean_promise_d"]).abs().argsort()].iloc[0]
print(f"\n  *** AT THE SAME PROMISE LENGTH ({same_len.mean_promise_d:.1f}d vs Olist's "
      f"{baseline['mean_promise_d']:.1f}d, q={same_len.q:.2f}):")
print(f"      late rate {same_len.late_rate_pct:.2f}% vs {baseline['late_rate_pct']:.2f}% - "
      f"{(1 - same_len.late_rate_pct / baseline['late_rate_pct']) * 100:.0f}% fewer late orders")
print("      for a customer-facing promise of identical length.")
print("\n      The buffer is not reduced, it is REALLOCATED - taken off the orders that never")
print("      needed it and given to the ones that did.")

# flat-buffer comparison at matched late rate
hdr("IS IT ACTUALLY BETTER THAN JUST PADDING SMARTER?  (flat buffer, matched risk)")
flat_pred = np.median(tr.actual_days) * np.ones(len(te))
rows = []
for add in range(0, 40):
    lr = (yte_days > (flat_pred + add)).mean() * 100
    rows.append({"flat_promise_d": flat_pred.mean() + add, "late_rate_pct": lr})
flat = pd.DataFrame(rows)
for r in results:
    match = flat[flat.late_rate_pct <= r["late_rate_pct"]].head(1)
    if len(match):
        fm = match.iloc[0]
        print(f"  at {r['late_rate_pct']:5.2f}% late:  risk-based needs {r['mean_promise_d']:5.1f}d   |   "
              f"flat buffer needs {fm.flat_promise_d:5.1f}d   -> risk-based is "
              f"{fm.flat_promise_d - r['mean_promise_d']:4.1f}d shorter")

# ═══════════════════════════════════════════════════════ B. classifier
hdr("MODEL B - P(LATE) CLASSIFIER under the promise actually given")
Xtr2, Xte2 = Xtr.copy(), Xte.copy()
Xtr2["promised_days"] = tr.promised_days.values
Xte2["promised_days"] = te.promised_days.values
clf = HistGradientBoostingClassifier(max_iter=350, learning_rate=0.06, max_depth=7, random_state=0)
clf.fit(Xtr2, tr.is_late.astype(int))
pl = clf.predict_proba(Xte2)[:, 1]
yl = te.is_late.astype(int).values
print(f"  ROC-AUC {roc_auc_score(yl, pl):.4f}   PR-AUC {average_precision_score(yl, pl):.4f}   "
      f"base rate {yl.mean() * 100:.2f}%")
dec = pd.qcut(pl, 10, labels=False, duplicates="drop")
tab = pd.DataFrame({"decile": dec, "late": yl, "p": pl}).groupby("decile").agg(
    n=("late", "size"), pred=("p", "mean"), actual_late_rate=("late", lambda s: s.mean() * 100))
tab["lift"] = tab.actual_late_rate / (yl.mean() * 100)
print("\n  risk deciles (calibration + lift):")
print(tab.round(3).to_string())
top = tab.iloc[-1]
print(f"\n  the riskiest 10% of orders contain {top.actual_late_rate:.1f}% late "
      f"({top.lift:.1f}x the base rate)")
cap = tab.iloc[-3:].n.sum()
caught = (tab.iloc[-3:].n * tab.iloc[-3:].actual_late_rate / 100).sum()
print(f"  contacting the riskiest 30% of orders ({cap:,}) reaches {caught:,.0f} of "
      f"{yl.sum():,} late orders ({caught / yl.sum() * 100:.0f}%)")

# ═══════════════════════════════════════════════════════ figure
fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.9))
ax = axes[0]
ax.plot(flat.flat_promise_d, flat.late_rate_pct, color=S.MUTED, linewidth=2,
        label="Flat buffer (one promise for everyone)")
ax.plot(res.mean_promise_d, res.late_rate_pct, color=S.C1, linewidth=2, marker="o",
        markersize=7, markerfacecolor=S.C1, markeredgecolor=S.SURFACE, markeredgewidth=2,
        label="Risk-based promise (per order)")
ax.scatter([baseline["mean_promise_d"]], [baseline["late_rate_pct"]], s=120, color=S.CRITICAL,
           zorder=5, edgecolor=S.SURFACE, linewidth=2, label="Olist today")
ax.annotate("Olist today", (baseline["mean_promise_d"], baseline["late_rate_pct"]),
            xytext=(10, 10), textcoords="offset points", fontsize=9.5, color=S.CRITICAL,
            fontweight="600")
ax.set_xlabel("Mean delivery promise (days)"); ax.set_ylabel("Orders delivered late (%)")
ax.set_title("Down and to the left is better", loc="left", fontsize=11.5)
ax.legend(loc="upper right", fontsize=8.5)
ax.set_ylim(0, 30); ax.set_xlim(5, 40)

ax = axes[1]
ax.bar(tab.index, tab.actual_late_rate, color=S.C1, width=0.68, zorder=3)
ax.axhline(yl.mean() * 100, color=S.CRITICAL, linewidth=1.4, zorder=4)
ax.annotate(f"platform average {yl.mean() * 100:.1f}%", (0, yl.mean() * 100), xytext=(2, 6),
            textcoords="offset points", fontsize=9, color=S.CRITICAL, fontweight="600")
ax.set_xlabel("Predicted-risk decile (10 = riskiest)"); ax.set_ylabel("Actually delivered late (%)")
ax.set_title(f"The model separates risk (AUC {roc_auc_score(yl, pl):.2f})", loc="left", fontsize=11.5)
ax.set_xticks(tab.index); ax.set_xticklabels(tab.index + 1)
fig.suptitle("Promise per order, not per platform", x=0.005, ha="left", fontsize=13.5, fontweight="600")
S.note(fig, f"Trained on {len(tr):,} orders to Apr 2018, tested on {len(te):,} unseen orders from May-Aug 2018. "
            "Every feature is knowable at checkout; seller history is built from the training window only.")
S.save(fig, "q7_risk_scorer", FIG)

# ═══════════════════════════════════════════════════════ ship the scores
te_out = te[["order_id", "customer_state", "primary_category", "primary_seller_id",
             "seller_customer_km", "promised_days", "actual_days", "is_late"]].copy()
te_out["risk_p_late"] = pl
te_out["recommended_promise_d"] = preds[0.90]
te_out.to_parquet(OUT / "risk_scores_test.parquet", index=False)
json.dump({"baseline": baseline, "quantile_policies": results,
           "auc": float(roc_auc_score(yl, pl)), "n_train": len(tr), "n_test": len(te)},
          open(OUT / "risk_model_summary.json", "w"), indent=2)
print(f"\n  -> {OUT / 'risk_scores_test.parquet'}   ({len(te_out):,} scored orders)")
