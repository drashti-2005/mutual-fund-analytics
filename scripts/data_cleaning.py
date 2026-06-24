"""
data_cleaning.py
================
Production-quality data cleaning pipeline for Mutual Fund Analytics.

Day 2 — Bluestock Fintech Internship
Author  : Data Engineering Team
Date    : 2026-06-24
Version : 1.0.0

Description:
    Cleans all 10 raw CSV datasets, validates business rules, flags anomalies,
    and saves cleaned versions to data/processed/. Generates a data quality
    report in reports/.

Usage:
    python scripts/data_cleaning.py
"""

# ---------------------------------------------------------------------------
# Standard Library
# ---------------------------------------------------------------------------
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Third-Party
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR       = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR   = PROJECT_ROOT / "reports"
LOG_DIR       = PROJECT_ROOT / "logs"
LOG_FILE      = LOG_DIR / "data_cleaning.log"

# Business-rule thresholds
EXPENSE_RATIO_MIN = 0.1
EXPENSE_RATIO_MAX = 2.5
NAV_MIN           = 0.0
AMOUNT_MIN        = 0.0

VALID_TRANSACTION_TYPES = {"SIP", "Lumpsum", "Redemption"}
VALID_KYC_STATUS        = {"Verified", "Pending"}

# Canonical transaction type mapping (handles common casing / typo variants)
TRANSACTION_TYPE_MAP = {
    "sip"        : "SIP",
    "lumpsum"    : "Lumpsum",
    "lump sum"   : "Lumpsum",
    "lump_sum"   : "Lumpsum",
    "redemption" : "Redemption",
    "redeem"     : "Redemption",
    "redumption" : "Redemption",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-8s | %(funcName)-35s | %(message)s"
    logger = logging.getLogger("data_cleaning")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        logger.handlers.clear()
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


logger = setup_logging()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_section(title: str) -> None:
    border = "=" * 70
    print(f"\n{border}\n  {title}\n{border}")


def save_processed(df: pd.DataFrame, filename: str) -> Path:
    """Save a DataFrame to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / filename
    df.to_csv(out, index=False)
    logger.info("Saved '%s' — %d rows, %d cols.", filename, len(df), df.shape[1])
    return out


def report_cleaning(
    name: str,
    original_rows: int,
    df: pd.DataFrame,
    issues: List[str],
) -> Dict:
    """Build a summary dict for the quality report."""
    removed = original_rows - len(df)
    return {
        "dataset"      : name,
        "original_rows": original_rows,
        "cleaned_rows" : len(df),
        "rows_removed" : removed,
        "issues_found" : issues,
    }


# ---------------------------------------------------------------------------
# 1. NAV History Cleaning
# ---------------------------------------------------------------------------

def clean_nav_history(filepath: Path) -> Tuple[pd.DataFrame, Dict]:
    """
    Clean 02_nav_history.csv.

    Steps:
        1. Parse 'date' to datetime.
        2. Sort by amfi_code + date.
        3. Forward-fill missing NAV for weekends/holidays.
        4. Remove duplicate (amfi_code, date) pairs.
        5. Validate NAV > 0; flag negatives.
    """
    print_section("Cleaning: nav_history")
    df = pd.read_csv(filepath, low_memory=False)
    original_rows = len(df)
    issues: List[str] = []
    logger.info("Loaded nav_history — %d rows.", original_rows)

    # 1. Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    invalid_dates = df["date"].isna().sum()
    if invalid_dates:
        issues.append(f"{invalid_dates} unparseable date values dropped.")
        df = df.dropna(subset=["date"])

    # 2. Sort
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # 3. Forward-fill missing NAV per scheme (weekends / holidays)
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    missing_before = df["nav"].isna().sum()
    df["nav"] = df.groupby("amfi_code")["nav"].transform(lambda s: s.ffill())
    missing_after = df["nav"].isna().sum()
    filled = missing_before - missing_after
    if filled:
        issues.append(f"{filled} NAV values forward-filled (weekends/holidays).")

    # 4. Remove duplicates on (amfi_code, date)
    dupes = df.duplicated(subset=["amfi_code", "date"]).sum()
    if dupes:
        df = df.drop_duplicates(subset=["amfi_code", "date"], keep="last")
        issues.append(f"{dupes} duplicate (amfi_code, date) rows removed.")

    # 5. Validate NAV > 0
    invalid_nav = (df["nav"] <= NAV_MIN).sum()
    if invalid_nav:
        issues.append(f"{invalid_nav} rows with NAV <= 0 flagged.")
        df["nav_valid"] = df["nav"] > NAV_MIN
    else:
        df["nav_valid"] = True

    # Compute daily return per scheme
    df["daily_return_pct"] = (
        df.groupby("amfi_code")["nav"]
        .pct_change()
        .mul(100)
        .round(4)
    )

    print(f"  Rows   : {original_rows:,} → {len(df):,}")
    print(f"  Issues : {len(issues)}")
    for i in issues:
        print(f"    • {i}")
    print(f"  Schemes: {df['amfi_code'].nunique()}")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    summary = report_cleaning("nav_history", original_rows, df, issues)
    return df, summary


# ---------------------------------------------------------------------------
# 2. Investor Transactions Cleaning
# ---------------------------------------------------------------------------

def clean_investor_transactions(filepath: Path) -> Tuple[pd.DataFrame, Dict]:
    """
    Clean 08_investor_transactions.csv.

    Steps:
        1. Parse transaction_date to datetime.
        2. Standardise transaction_type values.
        3. Validate amount_inr > 0.
        4. Validate kyc_status enum.
        5. Remove duplicates.
        6. Flag invalid records.
    """
    print_section("Cleaning: investor_transactions")
    df = pd.read_csv(filepath, low_memory=False)
    original_rows = len(df)
    issues: List[str] = []
    logger.info("Loaded investor_transactions — %d rows.", original_rows)

    # 1. Parse date
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad_dates = df["transaction_date"].isna().sum()
    if bad_dates:
        issues.append(f"{bad_dates} unparseable transaction_date values.")
        df = df.dropna(subset=["transaction_date"])

    # 2. Standardise transaction_type
    raw_types = df["transaction_type"].copy()
    df["transaction_type"] = (
        df["transaction_type"]
        .str.strip()
        .str.lower()
        .map(TRANSACTION_TYPE_MAP)
        .fillna(df["transaction_type"].str.strip())
    )
    # Capitalise first letter for any unmapped values
    df["transaction_type"] = df["transaction_type"].str.title()
    invalid_types = ~df["transaction_type"].isin(VALID_TRANSACTION_TYPES)
    if invalid_types.sum():
        issues.append(
            f"{invalid_types.sum()} rows with unrecognised transaction_type flagged."
        )
    df["transaction_type_valid"] = df["transaction_type"].isin(VALID_TRANSACTION_TYPES)

    # 3. Validate amount > 0
    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
    invalid_amount = (df["amount_inr"] <= AMOUNT_MIN) | df["amount_inr"].isna()
    if invalid_amount.sum():
        issues.append(f"{invalid_amount.sum()} rows with amount_inr <= 0 flagged.")
    df["amount_valid"] = ~invalid_amount

    # 4. Validate KYC status
    df["kyc_status"] = df["kyc_status"].str.strip().str.title()
    invalid_kyc = ~df["kyc_status"].isin(VALID_KYC_STATUS)
    if invalid_kyc.sum():
        df.loc[invalid_kyc, "kyc_status"] = "Pending"
        issues.append(
            f"{invalid_kyc.sum()} rows with invalid KYC status corrected to 'Pending'."
        )

    # 5. Remove duplicates
    dupes = df.duplicated().sum()
    if dupes:
        df = df.drop_duplicates()
        issues.append(f"{dupes} fully duplicate rows removed.")

    # 6. Overall validity flag
    df["record_valid"] = df["transaction_type_valid"] & df["amount_valid"]

    print(f"  Rows   : {original_rows:,} → {len(df):,}")
    print(f"  Issues : {len(issues)}")
    for i in issues:
        print(f"    • {i}")
    print(f"  Transaction types:\n{df['transaction_type'].value_counts().to_string()}")

    summary = report_cleaning("investor_transactions", original_rows, df, issues)
    return df, summary


# ---------------------------------------------------------------------------
# 3. Scheme Performance Cleaning
# ---------------------------------------------------------------------------

def clean_scheme_performance(filepath: Path) -> Tuple[pd.DataFrame, Dict]:
    """
    Clean 07_scheme_performance.csv.

    Steps:
        1. Convert return/metric columns to numeric.
        2. Validate expense_ratio_pct in [0.1, 2.5].
        3. Detect and flag anomalous return values (>200% or <-100%).
        4. Validate beta > 0.
    """
    print_section("Cleaning: scheme_performance")
    df = pd.read_csv(filepath, low_memory=False)
    original_rows = len(df)
    issues: List[str] = []
    logger.info("Loaded scheme_performance — %d rows.", original_rows)

    numeric_cols = [
        "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
        "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
        "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
        "aum_crore", "expense_ratio_pct",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Validate expense_ratio_pct
    if "expense_ratio_pct" in df.columns:
        bad_er = (
            (df["expense_ratio_pct"] < EXPENSE_RATIO_MIN) |
            (df["expense_ratio_pct"] > EXPENSE_RATIO_MAX)
        )
        if bad_er.sum():
            issues.append(
                f"{bad_er.sum()} rows with expense_ratio outside "
                f"[{EXPENSE_RATIO_MIN}%, {EXPENSE_RATIO_MAX}%] flagged."
            )
        df["expense_ratio_valid"] = ~bad_er

    # Detect anomalous returns (>200% or <-100%)
    for ret_col in ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct"]:
        if ret_col in df.columns:
            anomalies = (df[ret_col] > 200) | (df[ret_col] < -100)
            if anomalies.sum():
                issues.append(
                    f"{anomalies.sum()} anomalous values in '{ret_col}' flagged."
                )
            df[f"{ret_col}_anomaly"] = anomalies

    # Validate beta > 0
    if "beta" in df.columns:
        bad_beta = df["beta"] <= 0
        if bad_beta.sum():
            issues.append(f"{bad_beta.sum()} rows with beta <= 0 flagged.")
        df["beta_valid"] = ~bad_beta

    dupes = df.duplicated(subset=["amfi_code"]).sum()
    if dupes:
        df = df.drop_duplicates(subset=["amfi_code"], keep="last")
        issues.append(f"{dupes} duplicate amfi_code rows removed.")

    print(f"  Rows   : {original_rows:,} → {len(df):,}")
    print(f"  Issues : {len(issues)}")
    for i in issues:
        print(f"    • {i}")

    summary = report_cleaning("scheme_performance", original_rows, df, issues)
    return df, summary


# ---------------------------------------------------------------------------
# 4. Generic CSV Cleaning
# ---------------------------------------------------------------------------

def clean_generic(filepath: Path, name: str) -> Tuple[pd.DataFrame, Dict]:
    """
    General-purpose cleaning for datasets without complex business rules:
        1. Remove fully duplicate rows.
        2. Forward-fill or drop obvious missing values.
        3. Parse any column ending in '_date' or named 'date'/'month' to datetime.
        4. Strip whitespace from string columns.
    """
    print_section(f"Cleaning: {name}")
    df = pd.read_csv(filepath, low_memory=False)
    original_rows = len(df)
    issues: List[str] = []
    logger.info("Loaded %s — %d rows.", name, original_rows)

    # Strip whitespace from object columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Parse date columns
    date_cols = [
        c for c in df.columns
        if c.lower() in {"date", "month", "portfolio_date"}
        or c.lower().endswith("_date")
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        bad = df[col].isna().sum()
        if bad:
            issues.append(f"{bad} unparseable values in '{col}'.")

    # Remove duplicates
    dupes = df.duplicated().sum()
    if dupes:
        df = df.drop_duplicates()
        issues.append(f"{dupes} duplicate rows removed.")

    # Report missing values
    missing = df.isnull().sum().sum()
    if missing:
        issues.append(f"{missing} total missing values remain (retained for analysis).")

    print(f"  Rows   : {original_rows:,} → {len(df):,}")
    print(f"  Issues : {len(issues)}")
    for i in issues:
        print(f"    • {i}")

    summary = report_cleaning(name, original_rows, df, issues)
    return df, summary


# ---------------------------------------------------------------------------
# 5. Quality Report
# ---------------------------------------------------------------------------

def build_quality_report(summaries: List[Dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Data Quality Report — Day 2",
        "",
        f"**Generated:** {now}  ",
        "**Pipeline:** data_cleaning.py v1.0.0  ",
        "**Project:** Bluestock Fintech — Mutual Fund Analytics  ",
        "",
        "---",
        "",
        "## Cleaning Summary",
        "",
        "| Dataset | Original Rows | Cleaned Rows | Rows Removed |",
        "|---------|--------------|--------------|--------------|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['dataset']} | {s['original_rows']:,} | "
            f"{s['cleaned_rows']:,} | {s['rows_removed']:,} |"
        )
    lines += ["", "---", ""]

    for s in summaries:
        lines += [
            f"## Dataset: `{s['dataset']}`",
            "",
            f"- **Original rows:** {s['original_rows']:,}",
            f"- **Cleaned rows:** {s['cleaned_rows']:,}",
            f"- **Rows removed:** {s['rows_removed']:,}",
            "",
            "### Issues Found",
            "",
        ]
        if s["issues_found"]:
            for issue in s["issues_found"]:
                lines.append(f"- {issue}")
        else:
            lines.append("No issues found. Dataset is clean.")
        lines += ["", "---", ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
    start = datetime.now()
    logger.info("=" * 70)
    logger.info("Data Cleaning Pipeline — START")
    logger.info("=" * 70)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summaries: List[Dict] = []

    # --- Priority datasets with specific cleaning ---
    nav_df, s = clean_nav_history(RAW_DIR / "02_nav_history.csv")
    save_processed(nav_df, "02_nav_history_clean.csv")
    summaries.append(s)

    txn_df, s = clean_investor_transactions(RAW_DIR / "08_investor_transactions.csv")
    save_processed(txn_df, "08_investor_transactions_clean.csv")
    summaries.append(s)

    perf_df, s = clean_scheme_performance(RAW_DIR / "07_scheme_performance.csv")
    save_processed(perf_df, "07_scheme_performance_clean.csv")
    summaries.append(s)

    # --- Generic cleaning for remaining datasets ---
    generic_files = {
        "01_fund_master.csv"        : "01_fund_master_clean.csv",
        "03_aum_by_fund_house.csv"  : "03_aum_by_fund_house_clean.csv",
        "04_monthly_sip_inflows.csv": "04_monthly_sip_inflows_clean.csv",
        "05_category_inflows.csv"   : "05_category_inflows_clean.csv",
        "06_industry_folio_count.csv": "06_industry_folio_count_clean.csv",
        "09_portfolio_holdings.csv" : "09_portfolio_holdings_clean.csv",
        "10_benchmark_indices.csv"  : "10_benchmark_indices_clean.csv",
    }
    for raw_name, clean_name in generic_files.items():
        raw_path = RAW_DIR / raw_name
        if not raw_path.exists():
            logger.warning("File not found: %s — skipping.", raw_name)
            continue
        df, s = clean_generic(raw_path, raw_name.replace(".csv", ""))
        save_processed(df, clean_name)
        summaries.append(s)

    # --- Build & save quality report ---
    report = build_quality_report(summaries)
    report_path = REPORTS_DIR / "data_quality_report.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info("Quality report saved to '%s'.", report_path)

    elapsed = (datetime.now() - start).total_seconds()
    print_section("CLEANING PIPELINE COMPLETE")
    print(f"\n  Datasets cleaned : {len(summaries)}")
    print(f"  Output dir       : {PROCESSED_DIR}")
    print(f"  Quality report   : {report_path}")
    print(f"  Elapsed time     : {elapsed:.2f}s\n")
    logger.info("Cleaning pipeline completed in %.2fs.", elapsed)


if __name__ == "__main__":
    run_pipeline()
