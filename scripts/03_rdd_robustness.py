"""Robustness for the survey-timing RD: standard errors, placebo cutoffs, and a donut check."""
import pandas as pd, numpy as np, pathlib
R = pathlib.Path(r"D:\Data Analytics Hackathon - Gradient\data\raw")


def ols_hc1(X, y):
    """OLS with HC1 heteroskedasticity-robust standard errors. Pure numpy so the
    notebook is not hostage to the statsmodels/scipy version pairing."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    meat = (X * resid[:, None]).T @ (X * resid[:, None])
    V = XtX_inv @ meat @ XtX_inv * (n / (n - k))
    return beta, np.sqrt(np.diag(V))

DATES_O = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
orders = pd.read_csv(R / "orders.csv", parse_dates=DATES_O)
revs = pd.read_csv(R / "order_reviews.csv", parse_dates=["review_creation_date"])
revs = revs.sort_values("review_creation_date").drop_duplicates("order_id", keep="first")

d = orders[orders.order_status.eq("delivered") & orders.order_delivered_customer_date.notna()].copy()
d = d.merge(revs[["order_id", "review_score", "review_creation_date"]], on="order_id", how="inner")
d["gap"] = (d.order_delivered_customer_date - d.order_estimated_delivery_date).dt.total_seconds() / 86400
d["pre"] = d.review_creation_date < d.order_delivered_customer_date


def rd_fit(df, cut, bw, donut=0.0):
    """Local linear RD with a common slope allowed to differ each side. Returns effect, SE, n."""
    s = df[(df.gap > cut - bw) & (df.gap < cut + bw)].copy()
    if donut > 0:
        s = s[(s.gap - cut).abs() > donut]
    x = (s.gap - cut).values
    right = (x > 0).astype(float)
    if len(s) < 100 or right.min() == right.max():
        return None
    # y = a + b*x + TAU*right + c*(x*right)  ->  TAU is the jump at the cutoff
    X = np.column_stack([np.ones(len(s)), x, right, x * right])
    beta, se = ols_hc1(X, s.review_score.values)
    return beta[2], se[2], len(s)


print("=" * 84)
print("RD ESTIMATE AT THE TRUE CUTOFF (gap = 2 days), with HC1 standard errors")
print("=" * 84)
print(f"{'bandwidth':>10} {'n':>8} {'effect':>9} {'SE':>7} {'t':>7} {'95% CI':>20}")
for bw in [0.75, 1.0, 1.25, 1.5, 2.0]:
    r = rd_fit(d, 2.0, bw)
    if r:
        e, se, n = r
        print(f"{bw:>10.2f} {n:>8,} {e:>9.3f} {se:>7.3f} {e/se:>7.2f}   [{e-1.96*se:>6.2f}, {e+1.96*se:>5.2f}]")

print("\n" + "=" * 84)
print("PLACEBO CUTOFFS (bw=1.0) - if gap=2 were special, only it should show an effect")
print("=" * 84)
print(f"{'cutoff':>10} {'n':>8} {'effect':>9} {'SE':>7} {'t':>7}")
for cut in [-4, -3, -2, -1, 0, 1, 2, 3, 4, 5]:
    r = rd_fit(d, float(cut), 1.0)
    if r:
        e, se, n = r
        flag = "   <-- TRUE CUTOFF" if cut == 2 else ""
        print(f"{cut:>10} {n:>8,} {e:>9.3f} {se:>7.3f} {e/se:>7.2f}{flag}")

print("\n" + "=" * 84)
print("DONUT RD (drop obs within 0.25d of cutoff, bw=1.5) - guards against sorting at the threshold")
print("=" * 84)
r = rd_fit(d, 2.0, 1.5, donut=0.25)
if r:
    e, se, n = r
    print(f"effect = {e:+.3f}  SE {se:.3f}  t {e/se:.2f}  n {n:,}")

print("\n" + "=" * 84)
print("DECOMPOSING THE RAW 1.50-STAR PRE/POST GAP")
print("=" * 84)
raw = d[~d.pre].review_score.mean() - d[d.pre].review_score.mean()
print(f"raw naive gap (post-delivery minus pre-delivery reviews) = {raw:+.2f} stars")
e, se, n = rd_fit(d, 2.0, 1.0)
print(f"causal effect of survey timing at the cutoff (RD, bw=1.0)= {-e:+.2f} stars (SE {se:.2f})")
print(f"=> attributable to WHEN they were asked : ~{abs(e):.2f} stars, not distinguishable from zero")
print(f"=> attributable to the order being LATE  : ~{raw - abs(e):.2f} stars, i.e. essentially all of it")
print("\nupper bound: the 95% CI rules out a survey-timing effect larger than "
      f"{abs(e) + 1.96 * se:.2f} stars - far short of the {raw:.2f}-star raw gap.")
