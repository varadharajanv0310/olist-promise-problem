"""
TWO OPEN ANOMALIES.

1. RIO DE JANEIRO. Distance explains 87% of the variance in state delivery times - and completely
   fails on Rio. RJ sits 394km from its sellers (closer than Parana at 426km) yet runs a 13.5% late
   rate against Parana's 4.9%, on the platform's second-largest market. Something other than
   distance is happening there.

2. FEBRUARY-MARCH 2018. The worst months in the dataset (21.4% late, 3.74 stars) and demonstrably
   not a Black Friday effect - it is three months after. An unexplained worst-month is the first
   thing a reader will poke at.

For each: decompose the lead time into the three stages we can observe, and find out which one moved.
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


d = df[df.is_delivered & df.actual_days.notna()].copy()
d["purchase"] = pd.to_datetime(d.order_purchase_timestamp)
d["month"] = d.purchase.dt.to_period("M").dt.to_timestamp()

# ═══════════════════════════════════════════════════════════════════ 1. RIO
hdr("ANOMALY 1 - RIO DE JANEIRO: whose fault is it?")
PEERS = ["SP", "RJ", "MG", "PR", "SC", "RS", "ES"]
p = d[d.customer_state.isin(PEERS)].groupby("customer_state").agg(
    n=("order_id", "size"), med_km=("seller_customer_km", "median"),
    approve_h=("t_approve", lambda s: s.median() * 24),
    handoff=("t_handoff", "median"), transit=("t_transit", "median"),
    total=("actual_days", "median"), promised=("promised_days", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean")).sort_values("med_km")
print(p.round(2).to_string())

rj, pr = p.loc["RJ"], p.loc["PR"]
print(f"\n  RJ vs PR - near-identical distance ({rj.med_km:.0f} vs {pr.med_km:.0f} km):")
for lab, col in [("approval (h)", "approve_h"), ("seller handoff (d)", "handoff"),
                 ("carrier transit (d)", "transit"), ("TOTAL (d)", "total"),
                 ("promised (d)", "promised"), ("late rate (%)", "late")]:
    print(f"    {lab:<22} RJ {rj[col]:7.2f}   PR {pr[col]:7.2f}   diff {rj[col] - pr[col]:+7.2f}")
gap_total = rj.total - pr.total
print(f"\n  RJ takes {gap_total:+.2f} days longer than PR at the same distance, of which:")
print(f"    seller handoff  {rj.handoff - pr.handoff:+.2f}d  ({(rj.handoff - pr.handoff) / gap_total * 100:5.1f}%)")
print(f"    carrier transit {rj.transit - pr.transit:+.2f}d  ({(rj.transit - pr.transit) / gap_total * 100:5.1f}%)")
print("  => the delay is in the LAST MILE, not the seller. RJ sellers are not slower.")

# is it sellers located in RJ, or deliveries into RJ?
hdr("  Is it Rio as a DESTINATION or Rio as an ORIGIN?")
into = d[d.customer_state.eq("RJ")]
outof = d[d.seller_state.eq("RJ")]
outof_not_rj = d[d.seller_state.eq("RJ") & ~d.customer_state.eq("RJ")]
print(f"    orders INTO RJ (any seller)      n={len(into):>6,}  transit {into.t_transit.median():5.2f}d  "
      f"late {np.nanmean(into.is_late) * 100:5.2f}%")
print(f"    orders OUT OF RJ to elsewhere    n={len(outof_not_rj):>6,}  "
      f"transit {outof_not_rj.t_transit.median():5.2f}d  late {np.nanmean(outof_not_rj.is_late) * 100:5.2f}%")
print(f"    platform baseline                n={len(d):>6,}  transit {d.t_transit.median():5.2f}d  "
      f"late {np.nanmean(d.is_late) * 100:5.2f}%")
print("\n  => RJ as a DESTINATION is the problem. RJ sellers shipping elsewhere perform normally.")

hdr("  Which parts of Rio?")
cities = into.groupby("customer_city").agg(
    n=("order_id", "size"), transit=("t_transit", "median"), total=("actual_days", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean"))
cities = cities[cities.n >= 150].sort_values("late", ascending=False)
print(cities.round(2).head(10).to_string())
print(f"\n  spread across Rio municipalities: {cities.late.min():.1f}% to {cities.late.max():.1f}% late")
cap = cities.loc["rio de janeiro"] if "rio de janeiro" in cities.index else None
if cap is not None:
    rest = into[~into.customer_city.eq("rio de janeiro")]
    print(f"  Rio city itself: n={cap.n:,.0f}  late {cap.late:.2f}%  transit {cap.transit:.2f}d")
    print(f"  rest of RJ state: n={len(rest):,}  late {np.nanmean(rest.is_late) * 100:.2f}%  "
          f"transit {rest.t_transit.median():.2f}d")

# ═══════════════════════════════════════════════════════════════════ 2. FEB-MAR 2018
hdr("ANOMALY 2 - FEBRUARY-MARCH 2018: what actually moved?")
m = d.groupby("month").agg(
    n=("order_id", "size"), approve_h=("t_approve", lambda s: s.median() * 24),
    handoff=("t_handoff", "median"), transit=("t_transit", "median"),
    total=("actual_days", "median"), promised=("promised_days", "median"),
    late=("is_late", lambda s: np.nanmean(s) * 100), score=("review_score", "mean"))
m = m[m.index >= "2017-09-01"]
print(m.round(2).to_string())

base = m.loc["2017-12-01":"2018-01-01"]
crisis = m.loc["2018-02-01":"2018-03-01"]
after = m.loc["2018-04-01":"2018-05-01"]
print(f"\n  Dec17-Jan18 -> Feb-Mar18 -> Apr-May18:")
for lab, col in [("orders/mo", "n"), ("approval (h)", "approve_h"), ("handoff (d)", "handoff"),
                 ("transit (d)", "transit"), ("TOTAL (d)", "total"), ("promised (d)", "promised"),
                 ("late (%)", "late")]:
    print(f"    {lab:<14} {base[col].mean():8.2f} -> {crisis[col].mean():8.2f} -> {after[col].mean():8.2f}")
dt = crisis.total.mean() - base.total.mean()
print(f"\n  delivery time rose {dt:+.2f} days into the crisis, of which:")
print(f"    handoff  {crisis.handoff.mean() - base.handoff.mean():+.2f}d  "
      f"({(crisis.handoff.mean() - base.handoff.mean()) / dt * 100:5.1f}%)")
print(f"    transit  {crisis.transit.mean() - base.transit.mean():+.2f}d  "
      f"({(crisis.transit.mean() - base.transit.mean()) / dt * 100:5.1f}%)")
print(f"  volume change: {(crisis.n.mean() / base.n.mean() - 1) * 100:+.1f}%  "
      f"-> demand did NOT spike; this is a supply-side failure.")

hdr("  Was it everywhere, or somewhere?")
cr = d[(d.month >= "2018-02-01") & (d.month <= "2018-03-31")]
bs = d[(d.month >= "2017-12-01") & (d.month <= "2018-01-31")]
st = pd.DataFrame({
    "n_crisis": cr.groupby("customer_state").size(),
    "late_before": bs.groupby("customer_state").is_late.mean() * 100,
    "late_crisis": cr.groupby("customer_state").is_late.mean() * 100,
    "transit_before": bs.groupby("customer_state").t_transit.median(),
    "transit_crisis": cr.groupby("customer_state").t_transit.median()})
st = st[st.n_crisis >= 150]
st["late_delta"] = st.late_crisis - st.late_before
st["transit_delta"] = st.transit_crisis - st.transit_before
print(st.sort_values("late_delta", ascending=False).round(2).to_string())
print(f"\n  states worsening: {(st.late_delta > 0).sum()} of {len(st)}  "
      f"(median +{st.late_delta.median():.1f}pp)")
print("  => it is national and broad-based, not one route or one region.")

hdr("  Was it a few sellers, or all of them?")
sc = cr.groupby("primary_seller_id").agg(n=("order_id", "size"), late=("is_late", "mean"))
sb = bs.groupby("primary_seller_id").agg(n=("order_id", "size"), late=("is_late", "mean"))
j = sc.join(sb, lsuffix="_crisis", rsuffix="_before", how="inner")
j = j[(j.n_crisis >= 10) & (j.n_before >= 10)]
j["delta"] = (j.late_crisis - j.late_before) * 100
print(f"    sellers active in both windows with 10+ orders each: {len(j):,}")
print(f"    share whose late rate WORSENED: {(j.delta > 0).mean() * 100:.1f}%")
print(f"    median change: {j.delta.median():+.2f}pp   mean: {j.delta.mean():+.2f}pp")
print("  => the great majority of sellers got worse simultaneously. That is a shared")
print("     dependency failing - the carrier network - not seller behaviour.")

# ── FIG ──────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
ax = axes[0]
ax.scatter(p.med_km, p.late, s=90, color=S.C1, zorder=3, edgecolor=S.SURFACE, linewidth=2)
ax.scatter([rj.med_km], [rj.late], s=170, color=S.CRITICAL, zorder=4, edgecolor=S.SURFACE, linewidth=2)
for s_, row in p.iterrows():
    ax.annotate(s_, (row.med_km, row.late), xytext=(0, 11), textcoords="offset points",
                ha="center", fontsize=9.5,
                color=S.CRITICAL if s_ == "RJ" else S.INK_2,
                fontweight="600" if s_ == "RJ" else "normal")
ax.set_xlabel("Median seller→customer distance (km)"); ax.set_ylabel("Delivered late (%)")
ax.set_title("Rio breaks the distance rule", loc="left", fontsize=11.5)
ax.margins(0.16)

ax = axes[1]
ax.plot(m.index, m.transit, color=S.C1, linewidth=2, label="Carrier transit")
ax.plot(m.index, m.handoff, color=S.C4, linewidth=2, label="Seller handoff")
ax.axvspan(pd.Timestamp("2018-02-01"), pd.Timestamp("2018-03-31"), color=S.CRITICAL, alpha=0.10, zorder=1)
ax.annotate("Feb–Mar 2018", (pd.Timestamp("2018-02-20"), m.transit.max()), ha="center",
            fontsize=9.5, color=S.CRITICAL, fontweight="600")
ax.set_ylabel("Median days"); ax.legend(loc="upper left", fontsize=9)
ax.set_title("The crisis was entirely in transit", loc="left", fontsize=11.5)
fig.suptitle("Two anomalies, one answer: the carrier network", x=0.005, ha="left",
             fontsize=13.5, fontweight="600")
S.note(fig, "Rio's excess delay and the Feb–Mar 2018 collapse both sit in the carrier leg, not with "
            "sellers — and in Feb–Mar, order volume actually fell.")
S.save(fig, "q10_anomalies", FIG)
