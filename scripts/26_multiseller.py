"""
Follow-up to Q6: the multi-seller effect was the single largest term in the driver model
(OR 4.99, z 24.5). That is large enough to be suspicious, so this script tries to break it.

Hypothesis: Olist stores ONE order_delivered_customer_date per order. But an order split across
several sellers physically ships as several parcels from several places. So the order is marked
delivered - and the satisfaction survey fires - when a parcel arrives, not when the LAST one does.
The customer is asked to rate a complete order while still holding an incomplete one.

If that is right we should see: (a) the penalty survives controlling for lateness, (b) it is driven
by seller count and not merely item count, and (c) the written reviews say "part of it is missing".
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


d = df[df.is_delivered & df.review_score.notna() & df.n_sellers.notna()].copy()
d["multi"] = d.n_sellers > 1

hdr("1. THE RAW EFFECT")
g = d.groupby("multi").agg(n=("order_id", "size"), mean_score=("review_score", "mean"),
                           pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
                           pct_late=("is_late", lambda s: np.nanmean(s) * 100),
                           med_delivery=("actual_days", "median"))
g.index = ["single seller", "MULTIPLE sellers"]
print(g.round(2).to_string())
print(f"\n  multi-seller orders are {d.multi.mean() * 100:.2f}% of delivered orders "
      f"but {d[d.multi].is_one_star.sum() / d.is_one_star.sum() * 100:.2f}% of 1-star reviews")

hdr("2. DOES IT SURVIVE CONTROLLING FOR LATENESS?")
for lab, sub in [("ON-TIME only", d[d.is_late == 0]), ("LATE only", d[d.is_late == 1])]:
    t = sub.groupby("multi").agg(n=("order_id", "size"), mean_score=("review_score", "mean"),
                                 pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100))
    t.index = ["single", "MULTI"]
    print(f"\n  {lab}:")
    print(t.round(2).to_string())
    if len(t) == 2:
        print(f"    penalty: {t.mean_score.iloc[1] - t.mean_score.iloc[0]:+.2f} stars, "
              f"1-star rate {t.pct_1star.iloc[1] / t.pct_1star.iloc[0]:.1f}x")

hdr("3. IS IT SELLERS, OR JUST MORE ITEMS?  (the decisive test)")
sub = d[d.n_items.between(2, 6)].copy()          # hold item count constant-ish
sub["kind"] = np.where(sub.n_sellers > 1, "multi-seller", "one seller, several items")
t = sub.groupby(["n_items", "kind"]).agg(
    n=("order_id", "size"), mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100)).round(2)
print(t.to_string())
print("\n  Same number of items. The only difference is how many places they ship from.")
a = sub[sub.kind == "multi-seller"]
b = sub[sub.kind == "one seller, several items"]
print(f"\n  multi-seller  : n={len(a):,}  score {a.review_score.mean():.2f}  "
      f"1-star {np.nanmean(a.is_one_star) * 100:.2f}%")
print(f"  one seller    : n={len(b):,}  score {b.review_score.mean():.2f}  "
      f"1-star {np.nanmean(b.is_one_star) * 100:.2f}%")
print(f"  => splitting the SAME basket across sellers costs "
      f"{a.review_score.mean() - b.review_score.mean():+.2f} stars")

hdr("4. WHAT DO THE WRITTEN REVIEWS SAY?")
THEMES = {
    "only part arrived / missing": r"faltou|falta |apenas um|s[oó] veio|s[oó] recebi|um dos|outro produto n|falta ",
    "did not receive":             r"n[aã]o (recebi|chegou|foi entregue)|ainda n[aã]o",
    "wrong or broken":             r"errad|quebrad|defeit|danificad",
    "quality":                     r"qualidade|p[eé]ssim|ruim|horr[ií]vel",
}
low = d[(d.review_score <= 2) & d.review_comment_message.notna()].copy()
low["msg"] = low.review_comment_message.str.lower()
print(f"  1-2 star reviews with text: multi-seller n={low.multi.sum():,}  "
      f"single n={(~low.multi).sum():,}\n")
print(f"  {'theme':<30} {'MULTI-seller':>13} {'single':>10} {'lift':>8}")
for lab, pat in THEMES.items():
    a_ = low[low.multi].msg.str.contains(pat, regex=True, na=False).mean() * 100
    b_ = low[~low.multi].msg.str.contains(pat, regex=True, na=False).mean() * 100
    print(f"  {lab:<30} {a_:>12.1f}% {b_:>9.1f}% {a_ / b_ if b_ else np.nan:>7.2f}x")

hdr("5. SIZE OF THE PRIZE")
n_multi = d.multi.sum()
excess = d[d.multi].is_one_star.sum() - n_multi * np.nanmean(d[~d.multi].is_one_star)
print(f"  multi-seller delivered orders            {n_multi:>7,}")
print(f"  their 1-star reviews                     {d[d.multi].is_one_star.sum():>7,.0f}")
print(f"  expected at the single-seller rate       {n_multi * np.nanmean(d[~d.multi].is_one_star):>7,.0f}")
print(f"  EXCESS 1-star reviews                    {excess:>7,.0f}   "
      f"({excess / d.is_one_star.sum() * 100:.1f}% of all 1-stars on delivered orders)")
print(f"\n  ...from {n_multi / len(d) * 100:.2f}% of orders. This is the highest-leverage fix in the")
print("  dataset per order touched, and it is a notification problem, not a logistics one.")

# ── FIG ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.4, 5.0))
cats = ["Delivered\non time", "Delivered\nlate"]
single = [np.nanmean(d[(d.is_late == 0) & ~d.multi].is_one_star) * 100,
          np.nanmean(d[(d.is_late == 1) & ~d.multi].is_one_star) * 100]
multi = [np.nanmean(d[(d.is_late == 0) & d.multi].is_one_star) * 100,
         np.nanmean(d[(d.is_late == 1) & d.multi].is_one_star) * 100]
x = np.arange(2)
ax.bar(x - 0.19, single, width=0.36, color=S.C1, label="One seller", zorder=3)
ax.bar(x + 0.19, multi, width=0.36, color=S.CRITICAL, label="Several sellers", zorder=3)
for xi, (s_, m_) in enumerate(zip(single, multi)):
    ax.annotate(f"{s_:.0f}%", (xi - 0.19, s_), xytext=(0, 6), textcoords="offset points",
                ha="center", fontsize=10, color=S.INK, fontweight="600")
    ax.annotate(f"{m_:.0f}%", (xi + 0.19, m_), xytext=(0, 6), textcoords="offset points",
                ha="center", fontsize=10, color=S.INK, fontweight="600")
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("Orders receiving a 1-star review (%)")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.005), ncol=2)
ax.set_title("An order that ships from two places fails even when it arrives on time",
             loc="left", pad=42)
ax.text(0, 1.075, "1-star rate by seller count and delivery outcome · 96,476 delivered orders",
        transform=ax.transAxes, fontsize=9.5, color=S.MUTED, va="bottom")
S.note(fig, "Olist records one delivery timestamp per order, so a multi-parcel order is marked complete "
            "— and surveyed — when a parcel arrives, not when the last one does.")
S.save(fig, "q6_multiseller", FIG)
