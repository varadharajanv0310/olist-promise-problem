"""
CORE QUESTION 5 - Payment behaviour.
"How do payment type and installment choices relate to order value, and do they appear connected to
anything else in the customer's experience?"

The interesting answer is not the payment mix. It is that payment method is an OPERATIONAL variable:
a boleto is a printed bank slip the customer walks away and pays later, so the order sits unapproved
for a day and a bit before anyone picks it. That is a day of the delivery promise spent before the
seller has even been told to ship.
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


d = df[df.payment_type.notna() & df.payment_type.ne("not_defined")].copy()
d["approve_lag_h"] = d.t_approve * 24

# ═══════════════════════════════════════════════════════ the mix
hdr("Q5  THE PAYMENT MIX AND WHAT IT BUYS")
mix = d.groupby("payment_type").agg(
    orders=("order_id", "size"),
    order_value=("order_value", "mean"),
    med_value=("order_value", "median"),
    mean_inst=("max_installments", "mean"),
    approve_lag_h=("approve_lag_h", "median"),
    pct_not_delivered=("is_delivered", lambda s: (1 - s.mean()) * 100),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    mean_score=("review_score", "mean"),
    med_delivery=("actual_days", "median"),
)
mix["share"] = mix.orders / mix.orders.sum() * 100
print(mix[["orders", "share", "order_value", "med_value", "mean_inst", "approve_lag_h",
           "pct_not_delivered", "pct_late", "med_delivery", "mean_score"]].round(2).to_string())

# ═══════════════════════════════════════════════════════ installments
hdr("Q5  INSTALLMENTS AND ORDER VALUE")
cc = d[d.payment_type.eq("credit_card")].copy()
cc["inst_band"] = pd.cut(cc.max_installments, [0, 1, 2, 3, 6, 10, 24],
                         labels=["1 (upfront)", "2", "3", "4-6", "7-10", "11-24"])
ib = cc.groupby("inst_band", observed=True).agg(
    orders=("order_id", "size"), med_value=("order_value", "median"),
    mean_value=("order_value", "mean"), mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    med_delivery=("actual_days", "median"))
ib["share"] = ib.orders / ib.orders.sum() * 100
print(ib.round(2).to_string())
print(f"\n  correlation (credit-card orders): installments vs order value  r = "
      f"{cc.max_installments.corr(cc.order_value):+.3f}")
print(f"  median order value 1 installment R${ib.med_value.iloc[0]:.2f} -> "
      f"11-24 installments R${ib.med_value.iloc[-1]:.2f}  "
      f"({ib.med_value.iloc[-1] / ib.med_value.iloc[0]:.1f}x)")
print(f"  ...but the score barely moves: {ib.mean_score.iloc[0]:.2f} -> {ib.mean_score.iloc[-1]:.2f}")

# ═══════════════════════════════════════════════════════ the boleto chain
hdr("Q5  THE BOLETO CHAIN - payment method as an operational variable")
dd = d[d.is_delivered].copy()
chain = dd.groupby("payment_type").agg(
    n=("order_id", "size"),
    t_approve_h=("approve_lag_h", "median"),
    t_handoff_d=("t_handoff", "median"),
    t_transit_d=("t_transit", "median"),
    total_d=("actual_days", "median"),
    promised_d=("promised_days", "median"),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100))
print(chain.round(2).to_string())
bo, cr = chain.loc["boleto"], chain.loc["credit_card"]
print(f"\n  boleto vs credit card:")
print(f"    approval    {bo.t_approve_h:6.2f}h vs {cr.t_approve_h:5.2f}h   "
      f"(+{(bo.t_approve_h - cr.t_approve_h) / 24:.2f} days)")
print(f"    handoff     {bo.t_handoff_d:6.2f}d vs {cr.t_handoff_d:5.2f}d")
print(f"    transit     {bo.t_transit_d:6.2f}d vs {cr.t_transit_d:5.2f}d")
print(f"    TOTAL       {bo.total_d:6.2f}d vs {cr.total_d:5.2f}d   "
      f"(+{bo.total_d - cr.total_d:.2f} days)")
print(f"    late rate   {bo.pct_late:6.2f}% vs {cr.pct_late:5.2f}%")
share_from_approval = (bo.t_approve_h - cr.t_approve_h) / 24 / (bo.total_d - cr.total_d) * 100
print(f"\n  => {share_from_approval:.0f}% of boleto's extra delivery time is the approval wait alone,")
print(f"     spent before the seller is even told to ship.")

# ── FIG: the chain ───────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.8, 4.6))
order = ["credit_card", "debit_card", "voucher", "boleto"]
ch = chain.loc[order]
y = np.arange(len(ch))
stages = [("t_approve_h", "Awaiting payment approval", S.C2),
          ("t_handoff_d", "Seller preparing & handing to carrier", S.C4),
          ("t_transit_d", "In transit with the carrier", S.C1)]
left = np.zeros(len(ch))
for col, lab, c in stages:
    v = (ch[col] / 24 if col.endswith("_h") else ch[col]).values
    ax.barh(y, v, left=left, height=0.6, color=c, label=lab, zorder=3,
            edgecolor=S.SURFACE, linewidth=2)
    left += v
ax.set_yticks(y)
ax.set_yticklabels([o.replace("_", " ") for o in ch.index])
ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
ax.set_xlabel("Median days from purchase to delivery")
for i, tot in enumerate(left):
    ax.annotate(f"{tot:.1f}d", (tot, i), xytext=(7, 0), textcoords="offset points",
                va="center", fontsize=10, color=S.INK, fontweight="600")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2, columnspacing=1.4)
ax.set_title("A bank slip costs a day and a half before anyone picks the item", loc="left", pad=54)
ax.text(0, 1.13, "Median delivery time decomposed by stage and payment method",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "Boleto is a printed slip the customer pays later at a bank or lottery agent, so the order "
            "waits unapproved. That wait is inside the delivery promise the customer was already given.")
S.save(fig, "q5_payment_chain", FIG)

# ═══════════════════════════════════════════════════════ does it reach the review?
hdr("Q5  DOES PAYMENT METHOD REACH THE REVIEW?  (controlling for delivery outcome)")
piv = dd.pivot_table(index="payment_type", columns=dd.is_late == 1, values="review_score",
                     aggfunc="mean")
piv.columns = ["score_ontime", "score_late"]
piv = piv.join(dd.groupby("payment_type").size().rename("n"))
print(piv.round(3).to_string())
print(f"\n  raw score spread across methods : "
      f"{mix.mean_score.max() - mix.mean_score.min():.3f} stars")
print(f"  spread among ON-TIME orders only: {piv.score_ontime.max() - piv.score_ontime.min():.3f} stars")
print("  => most of the raw payment-method difference is delivery, not payment.")

hdr("Q5  VOUCHERS - the exception")
v = d[d.used_voucher == 1]
nv = d[d.used_voucher == 0]
print(f"  orders using a voucher     : n={len(v):,}  not-delivered {(1 - v.is_delivered.mean()) * 100:.2f}%  "
      f"score {v.review_score.mean():.2f}  value R${v.order_value.mean():.2f}")
print(f"  orders without a voucher   : n={len(nv):,}  not-delivered {(1 - nv.is_delivered.mean()) * 100:.2f}%  "
      f"score {nv.review_score.mean():.2f}  value R${nv.order_value.mean():.2f}")
print(f"\n  multi-record payments (split across methods): {(d.n_payment_records > 1).sum():,} orders, "
      f"not-delivered {(1 - d[d.n_payment_records > 1].is_delivered.mean()) * 100:.2f}%")
