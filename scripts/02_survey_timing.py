"""
Deep-dive: is the low score of late orders caused by lateness, or by being surveyed pre-delivery?

Identification: the survey fires at estimated_delivery_date + 2 days. So an order is surveyed
before it arrives iff (delivered - estimated) > 2 days. That is a sharp, mechanical cutoff in a
continuous running variable => regression discontinuity. A customer 1.9 days late and one 2.1 days
late had near-identical experiences but got a different survey. Any jump at the threshold is the
survey-timing effect, net of lateness.
"""
import pandas as pd, numpy as np, pathlib
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 50)
R = pathlib.Path(r"D:\Data Analytics Hackathon - Gradient\data\raw")

DATES_O = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
           "order_delivered_customer_date", "order_estimated_delivery_date"]
orders = pd.read_csv(R / "orders.csv", parse_dates=DATES_O)
revs = pd.read_csv(R / "order_reviews.csv", parse_dates=["review_creation_date", "review_answer_timestamp"])

# dedupe: 555 orders carry >1 survey. Keep the first survey sent for each order.
revs = revs.sort_values("review_creation_date").drop_duplicates("order_id", keep="first")

d = orders[orders.order_status.eq("delivered") & orders.order_delivered_customer_date.notna()].copy()
d = d.merge(revs[["order_id", "review_score", "review_creation_date", "review_comment_message"]],
            on="order_id", how="inner")
d["gap"] = (d.order_delivered_customer_date - d.order_estimated_delivery_date).dt.total_seconds() / 86400
d["pre"] = d.review_creation_date < d.order_delivered_customer_date
d["one_star"] = (d.review_score == 1).astype(int)


def hdr(t): print("\n" + "=" * 84 + "\n" + t + "\n" + "=" * 84)


# ---------------------------------------------------------------- TEST 1: the trigger rule
hdr("TEST 1 - WHAT EXACTLY TRIGGERS THE SURVEY?")
d["surv_minus_eta"] = (d.review_creation_date - d.order_estimated_delivery_date).dt.total_seconds() / 86400
d["surv_minus_deliv"] = (d.review_creation_date - d.order_delivered_customer_date.dt.normalize()).dt.total_seconds() / 86400
for label, sub in [("LATE  orders (gap>2)", d[d.gap > 2]), ("EARLY orders (gap<-2)", d[d.gap < -2])]:
    print(f"\n{label}   n={len(sub):,}")
    print(f"   survey - estimated_date : median {sub.surv_minus_eta.median():6.2f}d   "
          f"mode {sub.surv_minus_eta.round().mode().iloc[0]:.0f}d   "
          f"pct at exactly +2d = {(sub.surv_minus_eta.round() == 2).mean() * 100:5.1f}%")
    print(f"   survey - delivery_date  : median {sub.surv_minus_deliv.median():6.2f}d   "
          f"mode {sub.surv_minus_deliv.round().mode().iloc[0]:.0f}d   "
          f"pct at exactly +1d = {(sub.surv_minus_deliv.round() == 1).mean() * 100:5.1f}%")
print("\n=> the trigger is min(delivery, ETA) + ~1-2 days: whichever event comes first.")

# ---------------------------------------------------------------- TEST 2: first stage
hdr("TEST 2 - FIRST STAGE: does crossing gap=2 flip survey timing? (it must, for RDD to work)")
bins = np.arange(-4, 8.5, 0.5)
d["gb"] = pd.cut(d.gap, bins)
fs = d.groupby("gb", observed=True).agg(n=("pre", "size"), pct_pre=("pre", lambda s: s.mean() * 100))
fs = fs[fs.n >= 30]
print(fs.round(1).to_string())

# ---------------------------------------------------------------- TEST 3: the discontinuity
hdr("TEST 3 - THE DISCONTINUITY: mean score in fine bins around the gap=2 cutoff")
rd = d.groupby("gb", observed=True).agg(n=("review_score", "size"), mean_score=("review_score", "mean"),
                                        pct_1star=("one_star", lambda s: s.mean() * 100),
                                        pct_pre=("pre", lambda s: s.mean() * 100))
rd = rd[rd.n >= 30]
print(rd.round(2).to_string())

# ---------------------------------------------------------------- TEST 4: local linear RDD
hdr("TEST 4 - LOCAL LINEAR RD ESTIMATE (bandwidths around the cutoff)")
print(f"{'bandwidth':>12} {'n_left':>8} {'n_right':>8} {'fit_left':>10} {'fit_right':>10} {'JUMP':>9} {'jump_1star':>11}")
for bw in [1.0, 1.5, 2.0, 3.0, 4.0]:
    sub = d[(d.gap > 2 - bw) & (d.gap < 2 + bw)]
    L, Rt = sub[sub.gap <= 2], sub[sub.gap > 2]
    if len(L) < 30 or len(Rt) < 30:
        continue
    # linear fit each side, evaluated at the cutoff
    bl = np.polyfit(L.gap, L.review_score, 1); br = np.polyfit(Rt.gap, Rt.review_score, 1)
    fl, fr = np.polyval(bl, 2), np.polyval(br, 2)
    ol = np.polyfit(L.gap, L.one_star, 1); or_ = np.polyfit(Rt.gap, Rt.one_star, 1)
    j1 = (np.polyval(or_, 2) - np.polyval(ol, 2)) * 100
    print(f"{bw:>12.1f} {len(L):>8,} {len(Rt):>8,} {fl:>10.2f} {fr:>10.2f} {fr - fl:>9.2f} {j1:>10.1f}pp")

# ---------------------------------------------------------------- TEST 5: text evidence
hdr("TEST 5 - TEXT EVIDENCE: what do pre- vs post-delivery 1-star reviewers actually complain about?")
txt = d[d.review_comment_message.notna()].copy()
txt["msg"] = txt.review_comment_message.str.lower()
THEMES = {
    "NOT RECEIVED  ('nao recebi/chegou')": r"n[aã]o (recebi|chegou|foi entregue|entregue|receb)|ainda n[aã]o|nao recebi|nao chegou",
    "LATE          ('atraso/demora')":     r"atras|demor|prazo",
    "WRONG/BROKEN  ('errado/quebrado')":   r"errad|quebrad|defeit|danificad|avariad",
    "QUALITY       ('qualidade/pessimo')": r"qualidade|p[eé]ssim|ruim|horr[ií]vel",
    "ONLY PART     ('so um/faltou')":      r"faltou|falta |apenas um|s[oó] veio|s[oó] recebi",
}
one = txt[txt.review_score == 1]
print(f"1-star reviews with text: pre-delivery n={one.pre.sum():,}   post-delivery n={(~one.pre).sum():,}\n")
print(f"{'theme':<38} {'PRE-delivery':>13} {'POST-delivery':>14} {'lift':>8}")
for name, pat in THEMES.items():
    a = one[one.pre].msg.str.contains(pat, regex=True, na=False).mean() * 100
    b = one[~one.pre].msg.str.contains(pat, regex=True, na=False).mean() * 100
    print(f"{name:<38} {a:>12.1f}% {b:>13.1f}% {a / b if b else np.nan:>7.2f}x")

# ---------------------------------------------------------------- TEST 6: the prize
hdr("TEST 6 - SIZE OF THE PRIZE: what if the survey waited for actual delivery?")
# counterfactual: late orders that were surveyed POST-delivery, matched on how late they were
late = d[d.gap > 0].copy()
late["gap_bin"] = pd.cut(late.gap, [0, 2, 5, 10, 20, 1e9], labels=["0-2d", "2-5d", "5-10d", "10-20d", "20d+"])
cmp_ = late.groupby(["gap_bin", "pre"], observed=True).agg(
    n=("review_score", "size"), mean_score=("review_score", "mean"),
    pct_1star=("one_star", lambda s: s.mean() * 100)).round(2)
print(cmp_.to_string())
print("\nNOTE: the 2-5d/5-10d rows are where pre and post both have volume - that overlap is the")
print("      comparison that matters, since the cutoff makes pure post-delivery rare above 2 days.")

overlap = late[(late.gap > 2) & (late.gap < 10)]
if overlap.pre.nunique() == 2:
    a = overlap[overlap.pre].review_score.mean(); b = overlap[~overlap.pre].review_score.mean()
    na, nb = overlap.pre.sum(), (~overlap.pre).sum()
    print(f"\nwithin 2-10 days late:  pre-delivery {a:.2f} (n={na:,})   post-delivery {b:.2f} (n={nb:,})"
          f"   gap {b - a:+.2f} stars")

n_pre = d.pre.sum()
uplift_per = 0.0
print(f"\nplatform mean today (delivered orders) = {d.review_score.mean():.3f}")
for uplift in [0.5, 1.0, 1.5]:
    new = (d.review_score.sum() + n_pre * uplift) / len(d)
    print(f"   if each of the {n_pre:,} pre-delivery reviewers scored +{uplift:.1f} higher "
          f"-> platform mean {new:.3f}  ({new - d.review_score.mean():+.3f})")
