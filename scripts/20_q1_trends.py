"""
CORE QUESTION 1 - Marketplace performance over time.
"How have order volume, revenue and review scores trended? Do they all tell the same story?"

Short answer: no. Volume and revenue are the same story told twice; satisfaction is a different
story entirely, and the months where they diverge are the ones worth explaining.
"""
import pandas as pd, numpy as np, pathlib, sys
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import _style as S

S.apply()
ROOT = pathlib.Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data" / "processed" / "orders_analytical.parquet")
FIG = ROOT / "figures"


def hdr(t): print("\n" + "=" * 80 + "\n" + t + "\n" + "=" * 80)


# ═══════════════════════════════════════════════════════ monthly series
w = df[df.in_trend_window].copy()
w["month"] = pd.to_datetime(w.order_purchase_timestamp).dt.to_period("M").dt.to_timestamp()
m = w.groupby("month").agg(
    orders=("order_id", "size"),
    revenue=("order_value", "sum"),
    aov=("order_value", "mean"),
    mean_score=("review_score", "mean"),
    pct_1star=("is_one_star", lambda s: np.nanmean(s) * 100),
    pct_late=("is_late", lambda s: np.nanmean(s) * 100),
    med_delivery=("actual_days", "median"),
).reset_index()

hdr("Q1  MONTHLY SERIES (Jan 2017 - Aug 2018)")
disp = m.copy()
disp["month"] = disp.month.dt.strftime("%Y-%m")
disp["revenue"] = (disp.revenue / 1000).round(0)
print(disp.rename(columns={"revenue": "revenue_k"}).round(2).to_string(index=False))

first, last = m.iloc[0], m.iloc[-1]
hdr("Q1  GROWTH vs SATISFACTION - the divergence")
for lab, col, fmt in [("orders/month", "orders", "{:,.0f}"), ("revenue/month (R$)", "revenue", "{:,.0f}"),
                      ("avg order value (R$)", "aov", "{:.2f}"), ("mean review score", "mean_score", "{:.3f}"),
                      ("1-star rate (%)", "pct_1star", "{:.2f}"), ("late rate (%)", "pct_late", "{:.2f}")]:
    a, b = first[col], last[col]
    print(f"  {lab:<22} {fmt.format(a):>12}  ->  {fmt.format(b):>12}   ({(b / a - 1) * 100:+7.1f}%)")

# ═══════════════════════════════════════════════════════ FIG 1 - indexed
idx = m.set_index("month")[["orders", "revenue", "mean_score"]]
idx = idx / idx.iloc[0] * 100
fig, ax = plt.subplots(figsize=(9.5, 5.0))
for col, c, lab in [("orders", S.C1, "Order volume"), ("revenue", S.C2, "Revenue"),
                    ("mean_score", S.C3, "Mean review score")]:
    ax.plot(idx.index, idx[col], color=c, linewidth=2, label=lab, solid_capstyle="round")
    ax.annotate(f"{idx[col].iloc[-1]:.0f}", (idx.index[-1], idx[col].iloc[-1]),
                xytext=(8, 0), textcoords="offset points", color=S.INK_2, fontsize=9.5,
                va="center", fontweight="600")
ax.axhline(100, color=S.BASELINE, linewidth=0.8, zorder=1)
S.title(ax, "Growth and satisfaction are not the same story",
        "Indexed to January 2017 = 100 · Olist marketplace, Jan 2017 – Aug 2018")
ax.set_ylabel("Index (Jan 2017 = 100)")
ax.legend(loc="upper left", bbox_to_anchor=(0, 0.93))
ax.margins(x=0.06)
S.note(fig, "Revenue is the sum of item prices (freight excluded). Review score is the mean for orders "
            "placed in that month.")
S.save(fig, "q1_indexed_growth_vs_satisfaction", FIG)

# ═══════════════════════════════════════════════════════ FIG 2 - small multiples
fig, axes = plt.subplots(4, 1, figsize=(9.5, 9.0), sharex=True)
panels = [("orders", "Orders placed", S.C1, "{:,.0f}"),
          ("revenue", "Revenue (R$ 000s)", S.C2, "{:,.0f}"),
          ("mean_score", "Mean review score", S.C3, "{:.2f}"),
          ("pct_late", "Late deliveries (%)", S.CRITICAL, "{:.1f}")]
for ax, (col, lab, c, fmt) in zip(axes, panels):
    y = m[col] / 1000 if col == "revenue" else m[col]
    ax.plot(m.month, y, color=c, linewidth=2, solid_capstyle="round")
    ax.fill_between(m.month, y, y.min() * 0.96, color=c, alpha=0.07)
    ax.set_ylabel(lab, fontsize=9.5)
    ax.margins(x=0.03)
    peak = y.idxmax() if col != "mean_score" else y.idxmin()
    ax.annotate(fmt.format(y.loc[peak]), (m.month.loc[peak], y.loc[peak]), xytext=(0, 7),
                textcoords="offset points", ha="center", fontsize=9, color=S.INK_2, fontweight="600")
axes[0].set_title("Volume and revenue climb; satisfaction does not follow", loc="left", pad=16)
axes[-1].set_xlabel("Month of purchase")
S.note(fig, "Each panel is its own scale — the shapes are comparable, the levels are not.")
S.save(fig, "q1_small_multiples", FIG)

# ═══════════════════════════════════════════════════════ capacity test
hdr("Q1  DOES DEMAND OUTRUN CAPACITY?  (lagged correlation, monthly)")
mm = m.copy()
for lag in range(0, 4):
    c_late = mm.orders.corr(mm.pct_late.shift(-lag))
    c_score = mm.orders.corr(mm.mean_score.shift(-lag))
    print(f"  volume(t) vs late-rate(t+{lag}) r = {c_late:+.3f}   |   "
          f"volume(t) vs mean-score(t+{lag}) r = {c_score:+.3f}")

hdr("Q1  BLACK FRIDAY 2017 - the natural experiment")
d = df[df.order_purchase_timestamp.notna()].copy()
d["date"] = pd.to_datetime(d.order_purchase_timestamp).dt.date
daily = d.groupby("date").agg(orders=("order_id", "size"), score=("review_score", "mean"),
                              late=("is_late", lambda s: np.nanmean(s) * 100)).reset_index()
daily["date"] = pd.to_datetime(daily.date)
bf = daily[(daily.date >= "2017-11-15") & (daily.date <= "2017-12-05")]
print(bf.round(2).to_string(index=False))
base = daily[(daily.date >= "2017-10-15") & (daily.date < "2017-11-20")].orders.median()
peak = daily[(daily.date >= "2017-11-24") & (daily.date <= "2017-11-25")].orders.max()
print(f"\n  typical daily volume before  = {base:,.0f}")
print(f"  Black Friday peak            = {peak:,.0f}  ({peak / base:.1f}x)")

bfw = d[(pd.to_datetime(d.order_purchase_timestamp) >= "2017-11-24") &
        (pd.to_datetime(d.order_purchase_timestamp) < "2017-12-01")]
nov = d[(pd.to_datetime(d.order_purchase_timestamp) >= "2017-11-01") &
        (pd.to_datetime(d.order_purchase_timestamp) < "2017-11-24")]
print(f"\n  orders placed Black Friday week : n={len(bfw):,}  late={np.nanmean(bfw.is_late) * 100:.1f}%  "
      f"score={bfw.review_score.mean():.2f}  median delivery={bfw.actual_days.median():.1f}d")
print(f"  orders placed Nov 1-23          : n={len(nov):,}  late={np.nanmean(nov.is_late) * 100:.1f}%  "
      f"score={nov.review_score.mean():.2f}  median delivery={nov.actual_days.median():.1f}d")

# ═══════════════════════════════════════════════════════ FIG 3 - Black Friday
fig, ax = plt.subplots(figsize=(9.5, 4.6))
sl = daily[(daily.date >= "2017-10-01") & (daily.date <= "2018-01-15")]
ax.plot(sl.date, sl.orders, color=S.C1, linewidth=1.6, solid_capstyle="round")
bfd = pd.Timestamp("2017-11-24")
ax.axvline(bfd, color=S.CRITICAL, linewidth=1.4, zorder=1)
ax.annotate("Black Friday\n24 Nov 2017", (bfd, sl.orders.max()), xytext=(10, -6),
            textcoords="offset points", fontsize=9.5, color=S.CRITICAL, fontweight="600", va="top")
S.title(ax, "One day of demand the network was not built for",
        "Daily orders placed, Oct 2017 – Jan 2018")
ax.set_ylabel("Orders placed")
ax.margins(x=0.02)
S.note(fig, "Volume returns to trend within days; the delivery consequences do not.")
S.save(fig, "q1_black_friday", FIG)
