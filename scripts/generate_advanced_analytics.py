"""
generate_advanced_analytics.py
================================
Day 6 — Advanced Analytics Module for Bluestock Mutual Fund Analytics.

Executes all 6 tasks end-to-end and saves every output to the correct folder.

Tasks:
    Task 1 — Historical VaR & CVaR (95%) per fund
    Task 2 — Rolling 90-Day Sharpe Ratio (top 5 funds by AUM)
    Task 3 — Investor Cohort Analysis (by first transaction year)
    Task 4 — SIP Continuity Analysis (flag at-risk investors)
    Task 5 — Sector Concentration (HHI per equity fund)

Usage:
    python scripts/generate_advanced_analytics.py

Author : Data Engineering Team | Bluestock Fintech Internship
Date   : 2026-07-01
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Optional

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

warnings.filterwarnings("ignore")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("advanced_analytics")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
PROC        = ROOT / "data" / "processed"
REPORTS     = ROOT / "reports"
CHARTS_DIR  = ROOT / "reports" / "charts"

for d in [REPORTS, CHARTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

TRADING_DAYS    = 252
RISK_FREE_RATE  = 0.065
DAILY_RF        = RISK_FREE_RATE / TRADING_DAYS
PLOTLY_TEMPLATE = "plotly_white"


# ══════════════════════════════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> dict[str, pd.DataFrame]:
    """Load all required cleaned datasets."""
    log.info("Loading datasets …")
    datasets = {
        "fund_master" : pd.read_csv(PROC / "01_fund_master_clean.csv"),
        "nav_history" : pd.read_csv(PROC / "02_nav_history_clean.csv", parse_dates=["date"]),
        "performance" : pd.read_csv(PROC / "07_scheme_performance_clean.csv"),
        "transactions": pd.read_csv(PROC / "08_investor_transactions_clean.csv",
                                    parse_dates=["transaction_date"]),
        "portfolio"   : pd.read_csv(PROC / "09_portfolio_holdings_clean.csv"),
    }
    # Normalise transaction_type
    txn = datasets["transactions"]
    txn["transaction_type"] = (
        txn["transaction_type"].str.strip().str.title().replace({"Sip": "SIP"})
    )
    for name, df in datasets.items():
        log.info("  %-15s  %s", name, df.shape)
    return datasets


# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — Historical VaR & CVaR (95%)
# ══════════════════════════════════════════════════════════════════════════════

def compute_var_cvar(
    nav_df: pd.DataFrame,
    fund_master: pd.DataFrame,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """
    Compute Historical VaR and CVaR at the given confidence level for every fund.

    Parameters
    ----------
    nav_df      : NAV history DataFrame (must have amfi_code, daily_return_pct).
    fund_master : Fund master for scheme names.
    confidence  : Confidence level (default 0.95).

    Returns
    -------
    DataFrame sorted by highest risk (most negative VaR first).
    """
    log.info("Task 1 — Computing Historical VaR & CVaR (%.0f%%) …", confidence * 100)

    percentile = (1 - confidence) * 100   # 5th percentile for 95% VaR
    rows: list[dict] = []

    for amfi_code, grp in nav_df.groupby("amfi_code"):
        returns = grp["daily_return_pct"].dropna() / 100  # convert % → decimal
        if len(returns) < 30:
            continue
        var    = np.percentile(returns, percentile)
        cvar   = returns[returns <= var].mean()
        rows.append({
            "amfi_code": amfi_code,
            "var_95"   : round(var * 100, 4),   # back to %
            "cvar_95"  : round(cvar * 100, 4),
            "n_obs"    : len(returns),
        })

    result = pd.DataFrame(rows)
    result = result.merge(
        fund_master[["amfi_code", "scheme_name", "fund_house", "category"]],
        on="amfi_code", how="left",
    )
    result["short_name"] = (
        result["scheme_name"]
        .str.replace(r" - (Regular|Direct) Plan.*", "", regex=True)
        .str.slice(0, 30)
    )
    result.sort_values("var_95", inplace=True)   # most negative VaR first (highest risk)
    result.reset_index(drop=True, inplace=True)

    # Save
    out_path = REPORTS / "var_cvar_report.csv"
    result[["amfi_code", "short_name", "fund_house", "category",
            "var_95", "cvar_95", "n_obs"]].to_csv(out_path, index=False)
    log.info("  Saved: %s  (%d funds)", out_path.name, len(result))

    # Chart
    fig, ax = plt.subplots(figsize=(14, 8))
    x = np.arange(len(result))
    ax.barh(result["short_name"], result["var_95"],  color="#EF5350", alpha=0.8, label="VaR 95%")
    ax.barh(result["short_name"], result["cvar_95"], color="#B71C1C", alpha=0.5, label="CVaR 95%")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("Historical VaR & CVaR (95%) — All Funds\n(Sorted by Highest Risk)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Return (%)")
    ax.legend()
    plt.tight_layout()
    chart_path = CHARTS_DIR / "var_cvar_chart.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved chart: %s", chart_path.name)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Rolling 90-Day Sharpe Ratio
# ══════════════════════════════════════════════════════════════════════════════

def compute_rolling_sharpe(
    nav_df: pd.DataFrame,
    fund_master: pd.DataFrame,
    performance: pd.DataFrame,
    window: int = 90,
    top_n: int = 5,
) -> None:
    """
    Compute rolling 90-day Sharpe Ratio for the top N funds by AUM.
    Saves PNG and interactive HTML chart.
    """
    log.info("Task 2 — Rolling %d-Day Sharpe Ratio (top %d by AUM) …", window, top_n)

    # Select top N by AUM
    top_funds = (
        performance.nlargest(top_n, "aum_crore")[["amfi_code", "scheme_name", "aum_crore"]]
    )
    top_amfi  = top_funds["amfi_code"].tolist()

    short_name_map = dict(
        zip(
            performance["amfi_code"],
            performance["scheme_name"]
            .str.replace(r" - (Regular|Direct) Plan.*", "", regex=True)
            .str.slice(0, 25),
        )
    )

    fig_plotly = go.Figure()
    frames: list[pd.DataFrame] = []

    for amfi in top_amfi:
        name = short_name_map.get(amfi, str(amfi))
        grp  = (
            nav_df[nav_df["amfi_code"] == amfi]
            .sort_values("date")
            .copy()
        )
        grp["daily_return"] = grp["daily_return_pct"] / 100

        # Rolling Sharpe
        roll_mean = grp["daily_return"].rolling(window).mean()
        roll_std  = grp["daily_return"].rolling(window).std()
        grp["rolling_sharpe"] = (roll_mean - DAILY_RF) / roll_std * np.sqrt(TRADING_DAYS)

        valid = grp.dropna(subset=["rolling_sharpe"])
        frames.append(valid.assign(fund_name=name))

        fig_plotly.add_trace(go.Scatter(
            x=valid["date"],
            y=valid["rolling_sharpe"],
            mode="lines",
            name=name,
            hovertemplate=(
                f"<b>{name}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Sharpe: %{y:.3f}<extra></extra>"
            ),
        ))

    # Reference lines
    fig_plotly.add_hline(y=1.0, line_dash="dot", line_color="red",
                         annotation_text="Sharpe = 1.0", annotation_position="top right")
    fig_plotly.add_hline(y=0.0, line_dash="dot", line_color="gray",
                         annotation_text="Sharpe = 0")
    fig_plotly.update_layout(
        title=f"Rolling {window}-Day Sharpe Ratio — Top {top_n} Funds by AUM",
        xaxis_title="Date",
        yaxis_title="Rolling Sharpe Ratio",
        template=PLOTLY_TEMPLATE,
        height=550,
        legend=dict(orientation="h", y=1.02),
    )

    # Save HTML
    html_path = CHARTS_DIR / "rolling_sharpe_chart.html"
    fig_plotly.write_html(str(html_path))
    log.info("  Saved HTML: %s", html_path.name)

    # Save PNG (matplotlib)
    all_df = pd.concat(frames, ignore_index=True)
    fig_mpl, ax = plt.subplots(figsize=(14, 6))
    for name, grp_df in all_df.groupby("fund_name"):
        ax.plot(grp_df["date"], grp_df["rolling_sharpe"], lw=2, label=name)
    ax.axhline(1.0, color="red",  linestyle="--", lw=1.5, label="Sharpe=1.0")
    ax.axhline(0.0, color="gray", linestyle=":",  lw=1.0)
    ax.fill_between(
        all_df["date"].unique(),
        0, 1,
        alpha=0.05, color="green",
        label="Target zone (0–1)",
    )
    ax.set_title(f"Rolling {window}-Day Sharpe Ratio — Top {top_n} Funds by AUM",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Date"); ax.set_ylabel("Rolling Sharpe Ratio")
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    png_path = CHARTS_DIR / "rolling_sharpe_chart.png"
    fig_mpl.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig_mpl)
    log.info("  Saved PNG: %s", png_path.name)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Investor Cohort Analysis
# ══════════════════════════════════════════════════════════════════════════════

def investor_cohort_analysis(
    txn_df: pd.DataFrame,
    fund_master: pd.DataFrame,
) -> pd.DataFrame:
    """
    Group investors by the year of their first transaction.
    Compute cohort-level metrics: avg SIP amount, total invested,
    unique investors, and most preferred fund.
    """
    log.info("Task 3 — Investor Cohort Analysis …")

    sip = txn_df[txn_df["transaction_type"] == "SIP"].copy()
    sip["year"] = sip["transaction_date"].dt.year

    # First transaction year per investor
    first_year = (
        sip.groupby("investor_id")["year"]
        .min()
        .reset_index()
        .rename(columns={"year": "cohort_year"})
    )
    sip = sip.merge(first_year, on="investor_id")

    # Aggregate
    cohort_agg = (
        sip.groupby("cohort_year")
        .agg(
            avg_sip_amount   = ("amount_inr",   "mean"),
            total_invested   = ("amount_inr",   "sum"),
            unique_investors = ("investor_id",  "nunique"),
            transaction_count= ("amount_inr",   "count"),
        )
        .reset_index()
    )

    # Top preferred fund per cohort
    top_fund = (
        sip.groupby(["cohort_year", "amfi_code"])
        .size()
        .reset_index(name="txn_count")
        .sort_values("txn_count", ascending=False)
        .drop_duplicates("cohort_year")
        .merge(fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left")
        [["cohort_year", "scheme_name"]]
        .rename(columns={"scheme_name": "top_fund"})
    )

    cohort_agg = cohort_agg.merge(top_fund, on="cohort_year", how="left")
    cohort_agg["avg_sip_amount"] = cohort_agg["avg_sip_amount"].round(0)
    cohort_agg["total_invested"]  = cohort_agg["total_invested"].round(0)

    # Save
    out_path = REPORTS / "investor_cohort_analysis.csv"
    cohort_agg.to_csv(out_path, index=False)
    log.info("  Saved: %s", out_path.name)

    # Chart
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].bar(cohort_agg["cohort_year"].astype(str),
                cohort_agg["avg_sip_amount"], color="#42A5F5")
    axes[0].set_title("Avg SIP Amount by Cohort Year", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Cohort Year"); axes[0].set_ylabel("Avg SIP (₹)")

    axes[1].bar(cohort_agg["cohort_year"].astype(str),
                cohort_agg["unique_investors"], color="#66BB6A")
    axes[1].set_title("Unique Investors by Cohort Year", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Cohort Year"); axes[1].set_ylabel("Investors")

    plt.tight_layout()
    chart_path = CHARTS_DIR / "cohort_analysis_chart.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved chart: %s", chart_path.name)

    return cohort_agg


# ══════════════════════════════════════════════════════════════════════════════
# TASK 4 — SIP Continuity Analysis
# ══════════════════════════════════════════════════════════════════════════════

def sip_continuity_analysis(
    txn_df: pd.DataFrame,
    min_transactions: int = 6,
    gap_threshold_days: int = 35,
) -> pd.DataFrame:
    """
    Analyse SIP continuity per investor.
    Investors with average inter-SIP gap > gap_threshold_days are flagged
    as 'At Risk'; others are 'Healthy'.

    Only investors with at least `min_transactions` SIP transactions are evaluated.
    """
    log.info("Task 4 — SIP Continuity Analysis (min_txns=%d, gap_threshold=%dd) …",
             min_transactions, gap_threshold_days)

    sip = (
        txn_df[txn_df["transaction_type"] == "SIP"]
        .copy()
        .sort_values(["investor_id", "transaction_date"])
    )

    rows: list[dict] = []
    for inv_id, grp in sip.groupby("investor_id"):
        if len(grp) < min_transactions:
            continue
        dates = grp["transaction_date"].sort_values()
        gaps  = dates.diff().dt.days.dropna()
        avg_gap = gaps.mean()
        status  = "At Risk" if avg_gap > gap_threshold_days else "Healthy"
        rows.append({
            "investor_id"  : inv_id,
            "sip_count"    : len(grp),
            "avg_gap_days" : round(avg_gap, 1),
            "status"       : status,
        })

    result = pd.DataFrame(rows).sort_values("avg_gap_days", ascending=False)

    # Save
    out_path = REPORTS / "sip_continuity_report.csv"
    result.to_csv(out_path, index=False)
    log.info("  Saved: %s  (%d investors, %d At Risk)",
             out_path.name,
             len(result),
             (result["status"] == "At Risk").sum())

    # Chart
    status_counts = result["status"].value_counts()
    fig_pie = go.Figure(go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=0.45,
        marker_colors=["#EF5350", "#66BB6A"],
        textinfo="label+percent+value",
    ))
    fig_pie.update_layout(
        title="SIP Continuity Status — Investor Health Check",
        template=PLOTLY_TEMPLATE,
        height=450,
    )
    html_path = CHARTS_DIR / "sip_continuity_chart.html"
    fig_pie.write_html(str(html_path))

    # Matplotlib version
    fig_m, ax = plt.subplots(figsize=(7, 7))
    ax.pie(status_counts.values, labels=status_counts.index,
           autopct="%1.1f%%", colors=["#EF5350", "#66BB6A"],
           startangle=90, wedgeprops=dict(width=0.5))
    ax.set_title("SIP Continuity Status", fontsize=13, fontweight="bold")
    chart_path = CHARTS_DIR / "sip_continuity_chart.png"
    fig_m.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig_m)
    log.info("  Saved chart: %s", chart_path.name)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# TASK 5 — Sector Concentration (HHI)
# ══════════════════════════════════════════════════════════════════════════════

def sector_concentration_hhi(
    portfolio_df: pd.DataFrame,
    fund_master: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute Herfindahl-Hirschman Index (HHI) of sector weights per fund.
    HHI = Σ(weight_i / Σweights)²

    Classification:
        HHI < 0.15            → Diversified
        0.15 ≤ HHI < 0.25    → Moderately Concentrated
        HHI ≥ 0.25           → Highly Concentrated
    """
    log.info("Task 5 — Sector Concentration (HHI) …")

    rows: list[dict] = []
    for amfi, grp in portfolio_df.groupby("amfi_code"):
        sector_weights = grp.groupby("sector")["weight_pct"].sum()
        total_weight   = sector_weights.sum()
        if total_weight == 0:
            continue
        normalized = sector_weights / total_weight
        hhi = (normalized ** 2).sum()
        top_sector = sector_weights.idxmax()
        rows.append({
            "amfi_code"     : amfi,
            "hhi"           : round(hhi, 4),
            "top_sector"    : top_sector,
            "num_sectors"   : len(sector_weights),
        })

    result = pd.DataFrame(rows)
    result = result.merge(
        fund_master[["amfi_code", "scheme_name", "fund_house", "category"]],
        on="amfi_code", how="left",
    )
    result["short_name"] = (
        result["scheme_name"]
        .str.replace(r" - (Regular|Direct) Plan.*", "", regex=True)
        .str.slice(0, 30)
    )

    # Classification
    def classify_hhi(h: float) -> str:
        if h < 0.15:    return "Diversified"
        if h < 0.25:    return "Moderately Concentrated"
        return "Highly Concentrated"

    result["concentration"] = result["hhi"].apply(classify_hhi)
    result.sort_values("hhi", ascending=False, inplace=True)
    result.reset_index(drop=True, inplace=True)

    # Save
    out_path = REPORTS / "hhi_report.csv"
    result[["amfi_code", "short_name", "fund_house", "category",
            "hhi", "top_sector", "num_sectors", "concentration"]].to_csv(out_path, index=False)
    log.info("  Saved: %s  (%d funds)", out_path.name, len(result))

    # Chart
    COLOR_MAP = {
        "Highly Concentrated"    : "#D32F2F",
        "Moderately Concentrated": "#FFA726",
        "Diversified"            : "#388E3C",
    }
    bar_colors = [COLOR_MAP[c] for c in result["concentration"]]

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(result["short_name"], result["hhi"], color=bar_colors)
    ax.axvline(0.15, color="orange", linestyle="--", lw=1.5, label="HHI=0.15 (Moderate threshold)")
    ax.axvline(0.25, color="red",    linestyle="--", lw=1.5, label="HHI=0.25 (High threshold)")
    ax.set_title("Sector Concentration (HHI) — All Equity Funds", fontsize=13, fontweight="bold")
    ax.set_xlabel("HHI Score")
    legend_elements = [
        mpatches.Patch(color=v, label=k) for k, v in COLOR_MAP.items()
    ] + [
        plt.Line2D([0], [0], color="orange", linestyle="--", label="HHI=0.15"),
        plt.Line2D([0], [0], color="red",    linestyle="--", label="HHI=0.25"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)
    plt.tight_layout()
    chart_path = CHARTS_DIR / "hhi_concentration_chart.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved chart: %s", chart_path.name)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    log.info("=" * 65)
    log.info("  Day 6 — Advanced Analytics Pipeline — START")
    log.info("=" * 65)

    data = load_data()

    var_df     = compute_var_cvar(data["nav_history"], data["fund_master"])
    compute_rolling_sharpe(data["nav_history"], data["fund_master"], data["performance"])
    cohort_df  = investor_cohort_analysis(data["transactions"], data["fund_master"])
    sip_df     = sip_continuity_analysis(data["transactions"])
    hhi_df     = sector_concentration_hhi(data["portfolio"], data["fund_master"])

    log.info("=" * 65)
    log.info("  SUMMARY")
    log.info("  VaR/CVaR report      : %d funds", len(var_df))
    log.info("  Cohort analysis      : %d cohorts", len(cohort_df))
    log.info("  SIP continuity       : %d investors | At Risk: %d",
             len(sip_df), (sip_df["status"] == "At Risk").sum())
    log.info("  HHI report           : %d funds", len(hhi_df))
    log.info("  Charts saved to      : %s", CHARTS_DIR)
    log.info("  Reports saved to     : %s", REPORTS)
    log.info("=" * 65)
    log.info("  Day 6 Advanced Analytics COMPLETE ✅")


if __name__ == "__main__":
    main()
