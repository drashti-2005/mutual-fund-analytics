"""
generate_performance_charts.py — Day 4: Export all Performance Analytics charts as PNG.
Run: python scripts/generate_performance_charts.py
Uses matplotlib only — no kaleido, no Jupyter required.
"""
import warnings
warnings.filterwarnings("ignore")
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("perf_charts")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
PROC        = ROOT / "data" / "processed"
PERF_CHARTS = ROOT / "reports" / "performance_charts"
REPORTS     = ROOT / "reports"
PERF_CHARTS.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
RISK_FREE_RATE = 0.065
TRADING_DAYS   = 252
DAILY_RF       = RISK_FREE_RATE / TRADING_DAYS

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
plt.rcParams.update({"figure.dpi": 150})


def save(fig, name):
    fig.savefig(PERF_CHARTS / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved: %s", name)


# ── Load data ─────────────────────────────────────────────────────────────────
log.info("Loading datasets...")
fund_master  = pd.read_csv(PROC / "01_fund_master_clean.csv")
nav_history  = pd.read_csv(PROC / "02_nav_history_clean.csv", parse_dates=["date"])
sip_inflows  = pd.read_csv(PROC / "04_monthly_sip_inflows_clean.csv", parse_dates=["month"])
folio_count  = pd.read_csv(PROC / "06_industry_folio_count_clean.csv", parse_dates=["month"])
performance  = pd.read_csv(PROC / "07_scheme_performance_clean.csv")
portfolio    = pd.read_csv(PROC / "09_portfolio_holdings_clean.csv")
benchmark    = pd.read_csv(PROC / "10_benchmark_indices_clean.csv", parse_dates=["date"])
log.info("Data loaded.")

# ── Helper functions ──────────────────────────────────────────────────────────
def percentile_rank(series, ascending=True):
    ranked = series.rank(method="min", ascending=ascending)
    return (ranked - 1) / (len(series) - 1) * 100


def cagr(start_nav, end_nav, years):
    if any(pd.isna(x) for x in [start_nav, end_nav]) or start_nav <= 0 or years <= 0:
        return np.nan
    return (end_nav / start_nav) ** (1 / years) - 1


def cagr_for_fund(group, years):
    group = group.sort_values("date")
    end_date   = group["date"].max()
    start_date = end_date - pd.DateOffset(years=int(years))
    subset = group[group["date"] >= start_date]
    if len(subset) < 20:
        return np.nan
    actual_years = (subset.iloc[-1]["date"] - subset.iloc[0]["date"]).days / 365.25
    return cagr(subset.iloc[0]["nav"], subset.iloc[-1]["nav"], actual_years)


# ── Compute clean daily returns ───────────────────────────────────────────────
nav_returns = (
    nav_history.sort_values(["amfi_code", "date"])
    .assign(daily_return=lambda x: x.groupby("amfi_code")["nav"].pct_change())
)
clean_returns = nav_returns.dropna(subset=["daily_return"])
clean_returns = clean_returns[clean_returns["daily_return"].abs() <= 0.15]

# ── CAGR ──────────────────────────────────────────────────────────────────────
cagr_rows = []
for amfi, grp in nav_history.groupby("amfi_code"):
    cagr_rows.append({
        "amfi_code": amfi,
        "cagr_1yr": cagr_for_fund(grp, 1),
        "cagr_3yr": cagr_for_fund(grp, 3),
        "cagr_5yr": cagr_for_fund(grp, 5),
    })
cagr_df = pd.DataFrame(cagr_rows).merge(
    fund_master[["amfi_code", "scheme_name", "fund_house", "category", "expense_ratio_pct"]],
    on="amfi_code", how="left"
)
cagr_df["short_name"] = (
    cagr_df["scheme_name"].str.replace(r" - (Regular|Direct) Plan.*", "", regex=True).str.slice(0, 30)
)
cagr_df_sorted = cagr_df.sort_values("cagr_3yr", ascending=False).reset_index(drop=True)

# ── Sharpe & Sortino ──────────────────────────────────────────────────────────
ratio_rows = []
for amfi, grp in clean_returns.groupby("amfi_code"):
    r = grp["daily_return"].dropna()
    if len(r) < 30:
        continue
    ann_ret  = r.mean() * TRADING_DAYS
    ann_std  = r.std() * np.sqrt(TRADING_DAYS)
    sharpe   = (ann_ret - RISK_FREE_RATE) / ann_std if ann_std > 0 else np.nan
    neg_ret  = r[r < 0]
    downside = neg_ret.std() * np.sqrt(TRADING_DAYS) if len(neg_ret) > 5 else np.nan
    sortino  = (ann_ret - RISK_FREE_RATE) / downside if downside and downside > 0 else np.nan
    ratio_rows.append({"amfi_code": amfi, "ann_return": ann_ret,
                        "ann_volatility": ann_std, "sharpe": sharpe, "sortino": sortino})
ratio_df = pd.DataFrame(ratio_rows).merge(
    fund_master[["amfi_code", "scheme_name", "category"]].assign(
        short_name=lambda x: x["scheme_name"].str.replace(r" - (Regular|Direct) Plan.*", "", regex=True).str.slice(0, 30)
    ), on="amfi_code", how="left"
).sort_values("sharpe", ascending=False).reset_index(drop=True)

# ── Alpha / Beta ──────────────────────────────────────────────────────────────
bench_n100 = (
    benchmark[benchmark["index_name"] == "NIFTY100"]
    .sort_values("date").copy()
)
bench_n100["bench_return"] = bench_n100["close_value"].pct_change()
bench_n100 = bench_n100.dropna(subset=["bench_return"])[["date", "bench_return"]]

ab_rows = []
for amfi, grp in clean_returns.groupby("amfi_code"):
    fd = grp.rename(columns={"date": "date"})[["date", "daily_return"]]
    merged = fd.merge(bench_n100, on="date", how="inner").dropna()
    if len(merged) < 50:
        ab_rows.append({"amfi_code": amfi, "alpha": np.nan, "beta": np.nan,
                        "r_squared": np.nan, "p_value": np.nan})
        continue
    slope, intercept, r, p, se = stats.linregress(
        merged["bench_return"].values, merged["daily_return"].values
    )
    ab_rows.append({"amfi_code": amfi, "alpha": intercept * TRADING_DAYS,
                    "beta": slope, "r_squared": r**2, "p_value": p})
ab_df = pd.DataFrame(ab_rows).merge(
    fund_master[["amfi_code", "scheme_name", "category"]].assign(
        short_name=lambda x: x["scheme_name"].str.replace(r" - (Regular|Direct) Plan.*", "", regex=True).str.slice(0, 30)
    ), on="amfi_code", how="left"
).sort_values("alpha", ascending=False).reset_index(drop=True)

# ── Max Drawdown ──────────────────────────────────────────────────────────────
dd_rows = []
for amfi, grp in nav_history.groupby("amfi_code"):
    grp = grp.sort_values("date")
    nav  = grp["nav"].values
    rolling_max = np.maximum.accumulate(nav)
    drawdown    = nav / rolling_max - 1
    dd_rows.append({"amfi_code": amfi, "max_drawdown_pct": drawdown.min() * 100})
dd_df = pd.DataFrame(dd_rows).merge(
    fund_master[["amfi_code", "scheme_name", "category"]].assign(
        short_name=lambda x: x["scheme_name"].str.replace(r" - (Regular|Direct) Plan.*", "", regex=True).str.slice(0, 30)
    ), on="amfi_code", how="left"
).sort_values("max_drawdown_pct").reset_index(drop=True)

# ── Scorecard ─────────────────────────────────────────────────────────────────
scorecard = (
    cagr_df[["amfi_code", "short_name", "category", "fund_house", "expense_ratio_pct", "cagr_3yr"]]
    .merge(ratio_df[["amfi_code", "sharpe"]], on="amfi_code", how="left")
    .merge(ab_df[["amfi_code", "alpha"]], on="amfi_code", how="left")
    .merge(dd_df[["amfi_code", "max_drawdown_pct"]], on="amfi_code", how="left")
).dropna(subset=["cagr_3yr", "sharpe", "alpha"]).copy()

scorecard["pr_cagr"]    = percentile_rank(scorecard["cagr_3yr"],          ascending=True)
scorecard["pr_sharpe"]  = percentile_rank(scorecard["sharpe"],            ascending=True)
scorecard["pr_alpha"]   = percentile_rank(scorecard["alpha"],             ascending=True)
scorecard["pr_expense"] = percentile_rank(scorecard["expense_ratio_pct"], ascending=False)
scorecard["pr_dd"]      = percentile_rank(scorecard["max_drawdown_pct"],  ascending=False)
scorecard["score"]      = (
    scorecard["pr_cagr"]    * 0.30 +
    scorecard["pr_sharpe"]  * 0.25 +
    scorecard["pr_alpha"]   * 0.20 +
    scorecard["pr_expense"] * 0.15 +
    scorecard["pr_dd"]      * 0.10
)
RATING_COLORS = {"Excellent": "#1B5E20", "Very Good": "#388E3C",
                 "Good": "#66BB6A", "Average": "#FFA726", "Weak": "#EF5350"}

def assign_rating(s):
    if s >= 90: return "Excellent"
    if s >= 75: return "Very Good"
    if s >= 60: return "Good"
    if s >= 40: return "Average"
    return "Weak"

scorecard["rating"] = scorecard["score"].apply(assign_rating)
scorecard_sorted = scorecard.sort_values("score", ascending=False).reset_index(drop=True)

# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
log.info("Generating charts...")

# ── Chart 1: Daily Return Distribution ───────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 5))
r_all = clean_returns["daily_return"] * 100
sns.histplot(r_all, bins=60, kde=True, color="#5C6BC0", edgecolor="white", ax=axes[0])
axes[0].axvline(0, color="red", linestyle="--", lw=1.5, label="Zero")
axes[0].axvline(r_all.mean(), color="green", linestyle=":", lw=1.5, label=f"Mean: {r_all.mean():.3f}%")
axes[0].set_title("Daily Return Distribution — All Funds", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Daily Return (%)"); axes[0].set_ylabel("Frequency"); axes[0].legend()

merged_cat = clean_returns.merge(fund_master[["amfi_code", "category"]], on="amfi_code", how="left")
cats = merged_cat["category"].dropna().unique()
data_cat = [merged_cat[merged_cat["category"] == c]["daily_return"].values * 100 for c in cats]
axes[1].boxplot(data_cat, labels=cats, showfliers=False, patch_artist=True,
                boxprops=dict(facecolor="#90CAF9"))
axes[1].axhline(0, color="red", linestyle="--", lw=1)
axes[1].set_title("Daily Return Boxplot by Category", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Category"); axes[1].set_ylabel("Return (%)")
axes[1].tick_params(axis="x", rotation=30)
plt.tight_layout()
save(fig, "01_daily_return_distribution.png")

# ── Chart 2: CAGR Comparison ─────────────────────────────────────────────────
top20 = cagr_df_sorted.head(20)
x = np.arange(len(top20))
w = 0.26
fig, ax = plt.subplots(figsize=(14, 9))
ax.barh(x + w, top20["cagr_1yr"] * 100, height=w, label="1Y CAGR", color="#42A5F5")
ax.barh(x,     top20["cagr_3yr"] * 100, height=w, label="3Y CAGR", color="#66BB6A")
ax.barh(x - w, top20["cagr_5yr"] * 100, height=w, label="5Y CAGR", color="#FFA726")
ax.set_yticks(x); ax.set_yticklabels(top20["short_name"], fontsize=8)
ax.set_title("CAGR Comparison — Top 20 Funds (1Y / 3Y / 5Y)", fontsize=13, fontweight="bold")
ax.set_xlabel("CAGR (%)"); ax.legend()
plt.tight_layout()
save(fig, "02_cagr_comparison.png")

# ── Chart 3: Sharpe Ratio Bar ─────────────────────────────────────────────────
bar_c = ["#388E3C" if s >= 1.0 else "#F57C00" if s >= 0.5 else "#D32F2F"
         for s in ratio_df["sharpe"].fillna(0)]
fig, ax = plt.subplots(figsize=(12, 9))
ax.barh(ratio_df["short_name"], ratio_df["sharpe"], color=bar_c)
ax.axvline(1.0, color="red", linestyle="--", label="Sharpe=1.0")
ax.axvline(0.5, color="orange", linestyle=":", label="Sharpe=0.5")
ax.set_title("Sharpe Ratio Ranking — All Funds (RF=6.5%)", fontsize=13, fontweight="bold")
ax.set_xlabel("Sharpe Ratio"); ax.legend()
plt.tight_layout()
save(fig, "03_sharpe_ratio.png")

# ── Chart 4: Sharpe vs Sortino ────────────────────────────────────────────────
top15 = ratio_df.head(15)
x = np.arange(len(top15))
w = 0.38
fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(x - w/2, top15["sharpe"], width=w, label="Sharpe", color="#42A5F5")
ax.bar(x + w/2, top15["sortino"], width=w, label="Sortino", color="#66BB6A")
ax.set_xticks(x); ax.set_xticklabels(top15["short_name"], rotation=45, ha="right", fontsize=8)
ax.axhline(1.0, color="red", linestyle="--", label="Ratio=1.0")
ax.set_title("Sharpe vs Sortino — Top 15 Funds", fontsize=13, fontweight="bold")
ax.set_ylabel("Ratio Value"); ax.legend()
plt.tight_layout()
save(fig, "04_sharpe_vs_sortino.png")

# ── Chart 5: Alpha & Beta Scatter (Top 5) ────────────────────────────────────
top5_alpha = ab_df.head(5)
fig, axes = plt.subplots(1, 5, figsize=(20, 4), sharey=False)
for i, row in top5_alpha.iterrows():
    amfi = row["amfi_code"]
    name = row["short_name"]
    fd = clean_returns[clean_returns["amfi_code"] == amfi][["date", "daily_return"]]
    merged = fd.merge(bench_n100, on="date", how="inner").dropna()
    ax = axes[i]
    ax.scatter(merged["bench_return"] * 100, merged["daily_return"] * 100, s=5, alpha=0.4, color="#5C6BC0")
    m, b, *_ = stats.linregress(merged["bench_return"], merged["daily_return"])
    xs = np.linspace(merged["bench_return"].min(), merged["bench_return"].max(), 50)
    ax.plot(xs * 100, (m * xs + b) * 100, color="red", lw=2)
    ax.set_title(name[:20], fontsize=8, fontweight="bold")
    ax.set_xlabel("NIFTY100 Return (%)"); ax.set_ylabel("Fund Return (%)")
    if i >= 5:
        break
plt.suptitle("Alpha-Beta Regression — Top 5 Alpha Funds vs NIFTY100", fontsize=12, fontweight="bold")
plt.tight_layout()
save(fig, "05_alpha_beta_regression.png")

# ── Chart 6: Alpha Ranking Bar ────────────────────────────────────────────────
ab_plot = ab_df.dropna(subset=["alpha"]).sort_values("alpha", ascending=True)
colors_ab = ["#388E3C" if a > 0 else "#EF5350" for a in ab_plot["alpha"]]
fig, ax = plt.subplots(figsize=(12, 9))
ax.barh(ab_plot["short_name"], ab_plot["alpha"] * 100, color=colors_ab)
ax.axvline(0, color="black", lw=1)
ax.set_title("Annualized Alpha vs NIFTY100 — All Funds", fontsize=13, fontweight="bold")
ax.set_xlabel("Annualized Alpha (%)")
plt.tight_layout()
save(fig, "06_alpha_ranking.png")

# ── Chart 7: Maximum Drawdown Bar ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 9))
ax.barh(dd_df["short_name"].head(20), dd_df["max_drawdown_pct"].head(20), color="#EF5350")
ax.set_title("Maximum Drawdown — All Funds (Sorted Worst to Best)", fontsize=13, fontweight="bold")
ax.set_xlabel("Max Drawdown (%)")
plt.tight_layout()
save(fig, "07_max_drawdown.png")

# ── Chart 8: Drawdown over time (top 5 worst) ────────────────────────────────
worst5 = dd_df.head(5)
fig, ax = plt.subplots(figsize=(14, 6))
for _, row in worst5.iterrows():
    amfi = row["amfi_code"]
    name = row["short_name"]
    grp  = nav_history[nav_history["amfi_code"] == amfi].sort_values("date")
    nav  = grp["nav"].values
    rolling_max = np.maximum.accumulate(nav)
    drawdown    = (nav / rolling_max - 1) * 100
    ax.fill_between(grp["date"], drawdown, alpha=0.3, label=name)
    ax.plot(grp["date"], drawdown, lw=1)
ax.axhline(0, color="black", lw=0.8)
ax.set_title("Drawdown Over Time — 5 Worst Drawdown Funds", fontsize=13, fontweight="bold")
ax.set_xlabel("Date"); ax.set_ylabel("Drawdown (%)"); ax.legend(fontsize=8)
plt.tight_layout()
save(fig, "08_drawdown_chart.png")

# ── Chart 9: Fund Scorecard ───────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 10))
bar_colors_sc = [RATING_COLORS[r] for r in scorecard_sorted["rating"]]
ax.barh(scorecard_sorted["short_name"], scorecard_sorted["score"], color=bar_colors_sc)
ax.set_title("Fund Scorecard — Composite Score (0–100)", fontsize=13, fontweight="bold")
ax.set_xlabel("Score")
legend_elements = [mpatches.Patch(facecolor=v, label=k) for k, v in RATING_COLORS.items()]
ax.legend(handles=legend_elements, loc="lower right")
plt.tight_layout()
save(fig, "09_fund_scorecard.png")

# ── Chart 10: Benchmark Comparison ───────────────────────────────────────────
end_dt   = nav_history["date"].max()
start_dt = end_dt - pd.DateOffset(years=3)
top5_sc  = scorecard_sorted.head(5)

fig, ax = plt.subplots(figsize=(14, 6))
for idx_name, ls, color in [("NIFTY50", "--", "#D32F2F"), ("NIFTY100", ":", "#F57C00")]:
    b = benchmark[(benchmark["index_name"] == idx_name) & (benchmark["date"] >= start_dt)].sort_values("date")
    ax.plot(b["date"], b["close_value"] / b["close_value"].iloc[0] * 100,
            linestyle=ls, color=color, lw=2.5, label=idx_name)
for _, row in top5_sc.iterrows():
    amfi = row["amfi_code"]
    name = row["short_name"]
    fund_nav = nav_history[(nav_history["amfi_code"] == amfi) & (nav_history["date"] >= start_dt)].sort_values("date")
    if len(fund_nav) < 50:
        continue
    ax.plot(fund_nav["date"], fund_nav["nav"] / fund_nav["nav"].iloc[0] * 100, lw=1.8, label=name[:25])
ax.set_title("Top 5 Funds vs Benchmarks — 3-Year Cumulative Return", fontsize=13, fontweight="bold")
ax.set_xlabel("Date"); ax.set_ylabel("Indexed Return (Base=100)")
ax.axhline(100, color="gray", linestyle=":", lw=1); ax.legend(fontsize=8, loc="upper left")
plt.tight_layout()
save(fig, "10_benchmark_comparison.png")

# ── Chart 11: Cumulative Return (Top 5) ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6))
for _, row in top5_sc.iterrows():
    amfi = row["amfi_code"]
    name = row["short_name"]
    grp  = clean_returns[clean_returns["amfi_code"] == amfi].sort_values("date")
    cum  = (1 + grp["daily_return"]).cumprod()
    ax.plot(grp["date"], cum, lw=2, label=name[:25])
ax.set_title("Cumulative Return — Top 5 Scored Funds", fontsize=13, fontweight="bold")
ax.set_xlabel("Date"); ax.set_ylabel("Cumulative Return (1=start)"); ax.legend(fontsize=8)
plt.tight_layout()
save(fig, "11_cumulative_return.png")

# ── Chart 12: Rolling 30-Day Return Heatmap ──────────────────────────────────
rolling_frames = []
for _, row in top5_sc.iterrows():
    amfi = row["amfi_code"]
    name = row["short_name"]
    grp  = clean_returns[clean_returns["amfi_code"] == amfi].sort_values("date").copy()
    grp["rolling_30_ret"] = grp["daily_return"].rolling(30).mean() * TRADING_DAYS * 100
    grp["short_name"] = name
    rolling_frames.append(grp)
roll_df = pd.concat(rolling_frames, ignore_index=True)
pivot_heat = (
    roll_df[roll_df["rolling_30_ret"].notna()]
    .assign(month=lambda x: x["date"].dt.to_period("M"))
    .groupby(["short_name", "month"])["rolling_30_ret"].mean()
    .unstack("month")
)
fig, ax = plt.subplots(figsize=(18, 5))
sns.heatmap(pivot_heat, cmap="RdYlGn", center=0, linewidths=0.2, ax=ax,
            cbar_kws={"label": "Rolling 30d Ann. Return (%)"}, annot=False)
ax.set_title("Rolling 30-Day Return Heatmap — Top 5 Funds", fontsize=13, fontweight="bold")
ax.tick_params(axis="x", rotation=45, labelsize=7)
plt.tight_layout()
save(fig, "12_rolling_return_heatmap.png")

# ── Chart 13: Risk vs Return scatter ─────────────────────────────────────────
rv_df = ratio_df.merge(cagr_df[["amfi_code", "cagr_3yr"]], on="amfi_code", how="left")
rv_df = rv_df.merge(performance[["amfi_code", "aum_crore"]], on="amfi_code", how="left")
fig, ax = plt.subplots(figsize=(12, 7))
cats = rv_df["category"].dropna().unique()
colors_cat = plt.cm.tab10(np.linspace(0, 1, len(cats)))
for cat, col in zip(cats, colors_cat):
    sub = rv_df[rv_df["category"] == cat]
    ax.scatter(sub["ann_volatility"] * 100, sub["ann_return"] * 100,
               s=sub["aum_crore"].fillna(1000) / 1000,
               color=col, alpha=0.7, label=cat)
ax.axhline(RISK_FREE_RATE * 100, color="red", linestyle="--", lw=1, label="Risk-Free Rate")
ax.set_title("Risk vs Return — All Funds (Bubble = AUM)", fontsize=13, fontweight="bold")
ax.set_xlabel("Annualized Volatility (%)"); ax.set_ylabel("Annualized Return (%)")
ax.legend(fontsize=8); plt.tight_layout()
save(fig, "13_risk_return_scatter.png")

# ── Export CSVs ───────────────────────────────────────────────────────────────
log.info("Exporting CSVs...")

# performance_summary.csv
perf_summary = (
    cagr_df[["amfi_code", "scheme_name", "fund_house", "category", "expense_ratio_pct",
              "cagr_1yr", "cagr_3yr", "cagr_5yr"]]
    .merge(ratio_df[["amfi_code", "ann_return", "ann_volatility", "sharpe", "sortino"]], on="amfi_code", how="left")
    .merge(ab_df[["amfi_code", "alpha", "beta", "r_squared", "p_value"]], on="amfi_code", how="left")
    .merge(dd_df[["amfi_code", "max_drawdown_pct"]], on="amfi_code", how="left")
)
perf_summary.to_csv(REPORTS / "performance_summary.csv", index=False)

# alpha_beta.csv
ab_df.to_csv(REPORTS / "alpha_beta.csv", index=False)

# fund_scorecard.csv
scorecard_sorted.to_csv(REPORTS / "fund_scorecard.csv", index=False)

# tracking_error.csv (Top 5 vs NIFTY100)
te_rows = []
for _, row in top5_sc.iterrows():
    amfi = row["amfi_code"]
    name = row["short_name"]
    fund_nav = nav_history[
        (nav_history["amfi_code"] == amfi) & (nav_history["date"] >= start_dt)
    ].sort_values("date").copy()
    fund_nav["fund_return"] = fund_nav["nav"].pct_change()
    merged_te = fund_nav.merge(bench_n100, on="date", how="inner").dropna()
    if len(merged_te) < 50:
        continue
    diff = merged_te["fund_return"] - merged_te["bench_return"]
    te_rows.append({
        "fund_name": name, "amfi_code": amfi,
        "te_vs_nifty100_pct": diff.std() * np.sqrt(TRADING_DAYS) * 100,
        "ann_return_3yr": fund_nav["fund_return"].mean() * TRADING_DAYS * 100,
    })
pd.DataFrame(te_rows).to_csv(REPORTS / "tracking_error.csv", index=False)

# ── Manifest ───────────────────────────────────────────────────────────────────
all_files = sorted(list(PERF_CHARTS.glob("*.png")) + list(REPORTS.glob("*.csv")))
print("\n  EXPORT MANIFEST")
print(f"  {'File':<45} {'Size':>8}")
print("  " + "-" * 55)
for f in all_files:
    print(f"  {f.name:<45} {f.stat().st_size/1024:>6.1f} KB")
print(f"\n✅ Total PNGs : {len(list(PERF_CHARTS.glob('*.png')))}")
print(f"✅ Total CSVs : {len(list(REPORTS.glob('*.csv')))}")
print(f"\n✅ Day 4 Performance Analytics complete!")
