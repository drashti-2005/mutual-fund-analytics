"""
recommender.py
==============
Fund Recommendation Engine — Day 6 | Bluestock Fintech Internship

Recommends the top 3 mutual fund schemes based on an investor's risk appetite
using Sharpe Ratio, risk_grade, and return metrics from the cleaned dataset.

Usage:
    python scripts/recommender.py --risk Low
    python scripts/recommender.py --risk Moderate
    python scripts/recommender.py --risk High

Risk Levels:
    Low      → Debt / Liquid funds, risk_grade ∈ {Low, Low to Moderate}
    Moderate → Hybrid / Large Cap, risk_grade ∈ {Moderate}
    High     → Mid Cap / Small Cap / Equity, risk_grade ∈ {High, Very High}

Author : Data Engineering Team | Bluestock Fintech Internship
Date   : 2026-07-01
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
log = logging.getLogger("recommender")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

# ── Risk appetite → risk_grade mapping ───────────────────────────────────────
RISK_GRADE_MAP: dict[str, list[str]] = {
    "low"     : ["Low", "Low to Moderate"],
    "moderate": ["Moderate"],
    "high"    : ["High", "Very High"],
}

# ── Category preferences per risk level ──────────────────────────────────────
CATEGORY_PREF: dict[str, list[str]] = {
    "low"     : ["Debt", "Hybrid"],
    "moderate": ["Equity", "Hybrid"],
    "high"    : ["Equity"],
}


def load_performance() -> pd.DataFrame:
    """Load the cleaned scheme performance dataset."""
    path = PROC / "07_scheme_performance_clean.csv"
    if not path.exists():
        log.error("Performance dataset not found: %s", path)
        sys.exit(1)
    df = pd.read_csv(path)
    log.info("Loaded performance data: %d schemes", len(df))
    return df


def recommend(
    risk_appetite: str,
    top_n: int = 3,
) -> pd.DataFrame:
    """
    Recommend top mutual fund schemes based on risk appetite.

    Parameters
    ----------
    risk_appetite : One of 'Low', 'Moderate', 'High' (case-insensitive).
    top_n         : Number of recommendations to return (default 3).

    Returns
    -------
    DataFrame of recommended funds with key metrics.
    """
    key = risk_appetite.strip().lower()
    if key not in RISK_GRADE_MAP:
        log.error(
            "Invalid risk appetite '%s'. Choose from: Low, Moderate, High.", risk_appetite
        )
        sys.exit(1)

    grades     = RISK_GRADE_MAP[key]
    categories = CATEGORY_PREF[key]

    perf = load_performance()

    # Filter by risk_grade
    if "risk_grade" in perf.columns:
        filtered = perf[perf["risk_grade"].isin(grades)].copy()
    else:
        filtered = perf.copy()

    # Further filter by category if available
    if "category" in filtered.columns and len(filtered) > top_n:
        cat_filtered = filtered[filtered["category"].isin(categories)]
        if len(cat_filtered) >= top_n:
            filtered = cat_filtered

    # Drop rows missing Sharpe
    filtered = filtered.dropna(subset=["sharpe_ratio"])

    if len(filtered) == 0:
        log.warning("No funds match the criteria for risk='%s'. Showing top by Sharpe overall.", key)
        filtered = perf.dropna(subset=["sharpe_ratio"])

    # Rank by Sharpe Ratio (primary), then by 3Y return (secondary)
    filtered = filtered.sort_values(
        ["sharpe_ratio", "return_3yr_pct"], ascending=[False, False]
    ).reset_index(drop=True)

    recommendations = filtered.head(top_n)[
        [
            "amfi_code",
            "scheme_name",
            "fund_house",
            "category",
            "risk_grade",
            "sharpe_ratio",
            "return_3yr_pct",
            "expense_ratio_pct",
            "morningstar_rating",
        ]
    ].copy()

    return recommendations


def print_recommendations(df: pd.DataFrame, risk_appetite: str) -> None:
    """Pretty-print fund recommendations to stdout."""
    print()
    print("=" * 72)
    print(f"  FUND RECOMMENDATIONS — Risk Appetite: {risk_appetite.upper()}")
    print("=" * 72)

    for rank, row in df.iterrows():
        short = row["scheme_name"]
        if len(short) > 55:
            short = short[:52] + "…"
        print(f"\n  #{rank + 1}  {short}")
        print(f"       Fund House    : {row['fund_house']}")
        print(f"       Category      : {row['category']}")
        print(f"       Risk Grade    : {row['risk_grade']}")
        print(f"       Sharpe Ratio  : {row['sharpe_ratio']:.3f}")
        print(f"       3-Yr Return   : {row['return_3yr_pct']:.2f}%")
        print(f"       Expense Ratio : {row['expense_ratio_pct']:.2f}%")
        stars = "★" * int(row["morningstar_rating"]) + "☆" * (5 - int(row["morningstar_rating"]))
        print(f"       Rating        : {stars}  ({int(row['morningstar_rating'])}/5)")

    print()
    print("=" * 72)
    print("  Disclaimer: For educational purposes only. Not financial advice.")
    print("=" * 72)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mutual Fund Recommendation Engine — Bluestock Fintech",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--risk",
        required=True,
        choices=["Low", "Moderate", "High"],
        help="Investor risk appetite: Low | Moderate | High",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Number of fund recommendations to return (default: 3)",
    )
    args = parser.parse_args()

    log.info("Running recommender for risk appetite: %s", args.risk)
    recs = recommend(args.risk, top_n=args.top)
    print_recommendations(recs, args.risk)
    log.info("Done. %d recommendations generated.", len(recs))


if __name__ == "__main__":
    main()
