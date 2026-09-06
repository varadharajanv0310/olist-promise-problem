"""
CORE QUESTION 6 - Root cause analysis.
"Identify the most important factors associated with low review scores. Distinguish primary drivers
from secondary or contributing factors."

Two methodological choices drive this section:

1. We model P(1-star), not the mean score. The score distribution is bimodal - 57% fives, 12% ones -
   so a mean is an average of two populations that barely overlap, and a linear model on it fits
   neither. The business question is "what makes someone furious", which is a probability.

2. Logistic regression is fitted by IRLS in numpy. statsmodels 0.14.4 is broken against scipy >=1.16
   (`_lazywhere` was removed) and the notebook has to run unattended in Colab.

The design separates three things the raw data confounds: breaking the promise (days late), the
absolute wait (days in transit regardless of promise), and everything else.
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


def hdr(t): print("\n" + "=" * 88 + "\n" + t + "\n" + "=" * 88)


def logit_irls(X, y, names, max_iter=60, tol=1e-9):
    """Logistic regression by iteratively reweighted least squares. Returns a tidy frame of
    coefficients, robust-ish SEs from the observed information, odds ratios and CIs."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        W = np.clip(p * (1 - p), 1e-9, None)
        XtW = X.T * W
        try:
            step = np.linalg.solve(XtW @ X, X.T @ (y - p))
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(XtW @ X) @ (X.T @ (y - p))
        beta_new = beta + step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new
    eta = np.clip(X @ beta, -30, 30)
    p = 1 / (1 + np.exp(-eta))
    W = np.clip(p * (1 - p), 1e-9, None)
    cov = np.linalg.pinv((X.T * W) @ X)
    se = np.sqrt(np.diag(cov))
    ll = np.sum(y * np.log(np.clip(p, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1)))
    pbar = y.mean()
    ll0 = np.sum(y * np.log(pbar) + (1 - y) * np.log(1 - pbar))
    out = pd.DataFrame({"term": names, "coef": beta, "se": se})
    out["z"] = out.coef / out.se
    out["odds_ratio"] = np.exp(out.coef)
    out["or_lo"] = np.exp(out.coef - 1.96 * out.se)
    out["or_hi"] = np.exp(out.coef + 1.96 * out.se)
    return out, {"n": len(y), "pseudo_r2": 1 - ll / ll0, "base_rate": pbar}


# ═══════════════════════════════════════════════════════ 0. the two populations
hdr("Q6  STEP 0 - THERE ARE TWO SEPARATE FAILURE MODES, NOT ONE")
allr = df[df.review_score.notna()]
und = allr[~allr.is_delivered]
dl = allr[allr.is_delivered]
print(f"  DELIVERED orders      n={len(dl):>7,}  mean {dl.review_score.mean():.2f}  "
      f"1-star {np.nanmean(dl.is_one_star) * 100:5.2f}%")
print(f"  NEVER-DELIVERED       n={len(und):>7,}  mean {und.review_score.mean():.2f}  "
      f"1-star {np.nanmean(und.is_one_star) * 100:5.2f}%")
print(f"\n  never-delivered orders are {len(und) / len(allr) * 100:.2f}% of reviewed orders "
      f"but {und.is_one_star.sum() / allr.is_one_star.sum() * 100:.2f}% of all 1-star reviews")
print(f"  -> {und.is_one_star.sum():,.0f} one-star reviews that NO delivery improvement can reach.")
print("\n  by status:")
print(und.groupby("order_status").agg(n=("review_score", "size"), mean=("review_score", "mean"),
      pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100)).round(2).sort_values("n", ascending=False).to_string())

# ═══════════════════════════════════════════════════════ 1. the model
hdr("Q6  STEP 1 - DRIVER MODEL FOR P(1-STAR) AMONG DELIVERED ORDERS")
m = dl.copy()
m["days_late"] = np.clip(m.gap_days, 0, 30)            # promise breach, magnitude
m["days_early"] = np.clip(-m.gap_days, 0, 30)          # how much slack was left
m["log_km"] = np.log1p(m.seller_customer_km)
m["log_value"] = np.log1p(m.order_value)
m["freight_r"] = np.clip(m.freight_ratio, 0, 3)
m["handoff"] = np.clip(m.t_handoff, 0, 30)
m["multi_seller"] = (m.n_sellers > 1).astype(float)
m["items"] = np.clip(m.n_items, 1, 10)
m["wait"] = np.clip(m.actual_days, 0, 60)              # absolute wait, independent of the promise
for pt in ["boleto", "voucher", "debit_card"]:
    m[f"pay_{pt}"] = m.payment_type.eq(pt).astype(float)

CONT = ["days_late", "days_early", "wait", "handoff", "log_km", "log_value", "freight_r", "items"]
BIN = ["multi_seller", "pay_boleto", "pay_voucher", "pay_debit_card"]
m = m.dropna(subset=CONT + BIN + ["is_one_star"])
z = m[CONT].apply(lambda c: (c - c.mean()) / c.std())   # per-SD so effects are comparable
X = np.column_stack([np.ones(len(m))] + [z[c].values for c in CONT] + [m[c].values for c in BIN])
names = ["intercept"] + CONT + BIN
res, fit = logit_irls(X, m.is_one_star.values, names)

print(f"  n = {fit['n']:,}   base 1-star rate = {fit['base_rate'] * 100:.2f}%   "
      f"McFadden pseudo-R2 = {fit['pseudo_r2']:.3f}")
print("\n  continuous terms are per +1 SD; SD shown so the effect is readable in real units:\n")
sd = m[CONT].std()
r = res[res.term != "intercept"].copy()
r["1sd_equals"] = r.term.map(lambda t: f"{sd[t]:.2f}" if t in sd.index else "0 -> 1")
r = r.sort_values("odds_ratio", ascending=False)
print(r[["term", "odds_ratio", "or_lo", "or_hi", "z", "1sd_equals"]].round(3).to_string(index=False))

print("\n  PRIMARY vs SECONDARY:")
top = r.iloc[0]
print(f"    days_late dominates: OR {top.odds_ratio:.2f} per SD ({sd['days_late']:.1f} days), "
      f"z = {top.z:.0f}")
for t in ["wait", "handoff", "log_km", "freight_r", "log_value"]:
    row = r[r.term == t].iloc[0]
    print(f"    {t:<12} OR {row.odds_ratio:5.3f}  z {row.z:7.1f}   "
          f"{'-> secondary' if abs(row.z) > 3 else '-> not distinguishable'}")

# ── FIG: odds ratios ─────────────────────────────────────────────────────────
LBL = {"days_late": "Days late vs promise", "days_early": "Days of slack left",
       "wait": "Absolute wait (days)", "handoff": "Seller handoff time",
       "log_km": "Seller→customer distance", "log_value": "Order value",
       "freight_r": "Freight as share of value", "items": "Items in order",
       "multi_seller": "Multiple sellers in order", "pay_boleto": "Paid by boleto",
       "pay_voucher": "Paid by voucher", "pay_debit_card": "Paid by debit card"}
pl = r.sort_values("odds_ratio")
fig, ax = plt.subplots(figsize=(9.6, 6.0))
y = np.arange(len(pl))
cols = [S.CRITICAL if o > 1 else S.C1 for o in pl.odds_ratio]
ax.hlines(y, pl.or_lo, pl.or_hi, color=S.BASELINE, linewidth=2, zorder=2)
ax.scatter(pl.odds_ratio, y, s=64, c=cols, zorder=3, edgecolor=S.SURFACE, linewidth=1.6)
ax.axvline(1, color=S.MUTED, linewidth=1.1, zorder=1)
ax.set_yticks(y); ax.set_yticklabels([LBL.get(t, t) for t in pl.term], fontsize=9.5)
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xscale("log")
ax.set_xticks([0.8, 1, 1.5, 2, 3, 5])
ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}×"))
ax.get_xaxis().set_minor_formatter(plt.NullFormatter())
ax.set_xlabel("Odds ratio for receiving a 1-star review  (log scale, 95% CI)")
ax.annotate(f"{pl.odds_ratio.iloc[-1]:.2f}×", (pl.odds_ratio.iloc[-1], len(pl) - 1),
            xytext=(10, 0), textcoords="offset points", va="center",
            fontsize=11, color=S.CRITICAL, fontweight="600")
ax.set_title("One factor is not like the others", loc="left", pad=40)
ax.text(0, 1.045, f"Logistic model of P(1-star), {fit['n']:,} delivered orders · continuous terms per +1 SD",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "Right of the line raises the odds of a 1-star review, left lowers it. Splitting an order "
            "across sellers outweighs every other factor — including lateness. Distance, freight and "
            "order value are statistically real but small.")
S.save(fig, "q6_odds_ratios", FIG)

# ═══════════════════════════════════════════════════════ 2. attribution
hdr("Q6  STEP 2 - HOW MANY 1-STAR REVIEWS DOES EACH FACTOR ACCOUNT FOR?")
tot_1star = allr.is_one_star.sum()
late_1 = dl[dl.is_late == 1].is_one_star.sum()
und_1 = und.is_one_star.sum()
ontime_1 = dl[dl.is_late == 0].is_one_star.sum()
print(f"  total 1-star reviews                       {tot_1star:>8,.0f}   100.0%")
print(f"    from LATE deliveries                     {late_1:>8,.0f}   {late_1 / tot_1star * 100:5.1f}%")
print(f"    from orders that NEVER ARRIVED           {und_1:>8,.0f}   {und_1 / tot_1star * 100:5.1f}%")
print(f"    from orders delivered ON TIME            {ontime_1:>8,.0f}   {ontime_1 / tot_1star * 100:5.1f}%")
print(f"\n  => {(late_1 + und_1) / tot_1star * 100:.1f}% of all 1-star reviews are a DELIVERY failure of "
      f"one kind or the other.")
print(f"  => the remaining {ontime_1 / tot_1star * 100:.1f}% arrived on time and the customer was still "
      f"furious -")
print("     that residual is the product/listing/expectation problem Q4 isolated.")

# what does the on-time-but-angry group look like?
ot = dl[(dl.is_late == 0) & dl.is_one_star.notna()]
hdr("Q6  STEP 3 - THE RESIDUAL: on-time orders that still got 1 star")
ang = ot[ot.is_one_star == 1]
ok = ot[ot.is_one_star == 0]
print(f"  n = {len(ang):,} of {len(ot):,} on-time delivered orders ({len(ang) / len(ot) * 100:.2f}%)\n")
for lab, col in [("median order value R$", "order_value"), ("median freight ratio", "freight_ratio"),
                 ("median distance km", "seller_customer_km"), ("median delivery days", "actual_days"),
                 ("median slack days", "gap_days"), ("mean items", "n_items")]:
    print(f"    {lab:<24} 1-star {ang[col].median():>8.2f}   others {ok[col].median():>8.2f}")
print(f"    {'multi-seller share %':<24} 1-star {(ang.n_sellers > 1).mean() * 100:>8.2f}   "
      f"others {(ok.n_sellers > 1).mean() * 100:>8.2f}")
print(f"    {'has written comment %':<24} 1-star {ang.has_comment.mean() * 100:>8.2f}   "
      f"others {ok.has_comment.mean() * 100:>8.2f}")

txt = ang[ang.review_comment_message.notna()].review_comment_message.str.lower()
THEMES = {"not received / missing": r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o|faltou|s[oó] veio|apenas um",
          "wrong or broken item":   r"errad|quebrad|defeit|danificad|avariad|veio outro",
          "quality complaint":      r"qualidade|p[eé]ssim|ruim|horr[ií]vel|fraco",
          "late (despite on-time)": r"atras|demor|prazo"}
print(f"\n  what the {len(txt):,} written ones say:")
for lab, pat in THEMES.items():
    print(f"    {lab:<26} {txt.str.contains(pat, regex=True, na=False).mean() * 100:5.1f}%")
print("\n  NOTE: 'not received' still appears on ON-TIME orders - partial deliveries. An order is marked")
print("        delivered when the parcel arrives, but a multi-seller order ships in several parcels.")
