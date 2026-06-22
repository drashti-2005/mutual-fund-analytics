"""
data_ingestion.py
=================
Production-quality data ingestion pipeline for Mutual Fund Analytics.

Day 1 — Bluestock Fintech Internship
Author  : Data Engineering Team
Date    : 2026-06-22
Version : 1.0.0

Description:
    Loads all CSV datasets from data/raw/, performs comprehensive data profiling,
    validates data quality, and saves a structured report to reports/.

Usage:
    python scripts/data_ingestion.py
"""

# ---------------------------------------------------------------------------
# Standard Library Imports
# ---------------------------------------------------------------------------
import os
import sys
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Third-Party Imports
# ---------------------------------------------------------------------------
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIGURATION — Edit these variables to match your environment
# ---------------------------------------------------------------------------

# Project root is one level up from this script
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_FILE = LOG_DIR / "data_ingestion.log"

# Statistical outlier threshold (IQR multiplier)
OUTLIER_IQR_MULTIPLIER = 1.5

# Minimum acceptable non-null percentage per column (%)
MIN_COMPLETENESS_THRESHOLD = 70.0

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure and return a logger with console + file handlers."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(funcName)-30s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger("data_ingestion")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers when module is reloaded
    if logger.handlers:
        logger.handlers.clear()

    # Console handler — INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(ch)

    # File handler — DEBUG and above
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(fh)

    return logger


logger = setup_logging()

# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

def print_section(title: str, width: int = 70) -> None:
    """Print a formatted section header to stdout."""
    border = "=" * width
    print(f"\n{border}")
    print(f"  {title}")
    print(f"{border}")


def print_subsection(title: str, width: int = 70) -> None:
    """Print a formatted sub-section header to stdout."""
    border = "-" * width
    print(f"\n{border}")
    print(f"  {title}")
    print(f"{border}")


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def discover_csv_files(directory: Path) -> List[Path]:
    """
    Discover all CSV files in the given directory (non-recursive).

    Args:
        directory: Path to the directory to scan.

    Returns:
        Sorted list of CSV file paths.

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    if not directory.exists():
        raise FileNotFoundError(f"Data directory not found: {directory}")

    csv_files = sorted(directory.glob("*.csv"))
    logger.info("Discovered %d CSV file(s) in '%s'.", len(csv_files), directory)
    return csv_files


def load_csv(filepath: Path) -> Optional[pd.DataFrame]:
    """
    Safely load a CSV file into a Pandas DataFrame.

    Args:
        filepath: Absolute path to the CSV file.

    Returns:
        DataFrame on success, None on failure.
    """
    try:
        df = pd.read_csv(filepath, low_memory=False)
        logger.info("Loaded '%s' — shape: %s.", filepath.name, df.shape)
        return df
    except pd.errors.EmptyDataError:
        logger.warning("'%s' is empty — skipping.", filepath.name)
        return None
    except pd.errors.ParserError as exc:
        logger.error("Parse error in '%s': %s", filepath.name, exc)
        return None
    except OSError as exc:
        logger.error("OS error reading '%s': %s", filepath.name, exc)
        return None


def load_all_datasets(directory: Path) -> Dict[str, pd.DataFrame]:
    """
    Load every CSV in the directory into a dict keyed by filename (no extension).

    Args:
        directory: Path to the raw data directory.

    Returns:
        Dictionary mapping dataset name -> DataFrame.
    """
    csv_files = discover_csv_files(directory)
    datasets: Dict[str, pd.DataFrame] = {}

    for filepath in csv_files:
        df = load_csv(filepath)
        if df is not None:
            datasets[filepath.stem] = df

    logger.info("Successfully loaded %d dataset(s).", len(datasets))
    return datasets


# ---------------------------------------------------------------------------
# Data Profiling
# ---------------------------------------------------------------------------

def detect_outliers_iqr(series: pd.Series) -> Tuple[int, float, float]:
    """
    Detect outliers in a numeric Series using the IQR method.

    Args:
        series: Numeric pandas Series.

    Returns:
        Tuple of (outlier_count, lower_fence, upper_fence).
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - OUTLIER_IQR_MULTIPLIER * iqr
    upper = q3 + OUTLIER_IQR_MULTIPLIER * iqr
    outlier_count = int(((series < lower) | (series > upper)).sum())
    return outlier_count, round(lower, 4), round(upper, 4)


def profile_dataset(name: str, df: pd.DataFrame) -> Dict:
    """
    Generate a comprehensive data quality profile for a DataFrame.

    Args:
        name : Dataset identifier (used in logging/reporting).
        df   : Input DataFrame.

    Returns:
        Dictionary with all profiling metrics.
    """
    logger.info("Profiling dataset: '%s'.", name)

    total_rows, total_cols = df.shape

    # --- Missing values ---
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / total_rows * 100).round(2)
    missing_summary = pd.DataFrame({
        "missing_count": missing_counts,
        "missing_pct": missing_pct,
        "completeness_pct": (100 - missing_pct).round(2),
        "dtype": df.dtypes.astype(str),
    })

    # --- Duplicates ---
    duplicate_count = int(df.duplicated().sum())

    # --- Data type classification ---
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    object_cols = df.select_dtypes(include=["object"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # --- Outlier detection (numeric columns only) ---
    outlier_info: Dict[str, Dict] = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) > 10:
            count, lower, upper = detect_outliers_iqr(series)
            outlier_info[col] = {
                "outlier_count": count,
                "lower_fence": lower,
                "upper_fence": upper,
                "outlier_pct": round(count / total_rows * 100, 2),
            }

    # --- Basic statistics ---
    try:
        basic_stats = df.describe(include="all").round(4)
    except Exception as exc:
        logger.warning("Could not generate describe() for '%s': %s", name, exc)
        basic_stats = pd.DataFrame()

    # --- Columns with data type issues (object cols that look numeric) ---
    dtype_issues: List[str] = []
    for col in object_cols:
        sample = df[col].dropna().head(100)
        numeric_convertible = pd.to_numeric(sample, errors="coerce").notna().sum()
        if numeric_convertible / max(len(sample), 1) > 0.8:
            dtype_issues.append(col)

    profile = {
        "name": name,
        "shape": {"rows": total_rows, "columns": total_cols},
        "missing_summary": missing_summary,
        "duplicate_count": duplicate_count,
        "numeric_columns": numeric_cols,
        "object_columns": object_cols,
        "datetime_columns": datetime_cols,
        "outlier_info": outlier_info,
        "basic_stats": basic_stats,
        "dtype_issues": dtype_issues,
        "columns_below_threshold": missing_summary[
            missing_summary["completeness_pct"] < MIN_COMPLETENESS_THRESHOLD
        ].index.tolist(),
    }

    return profile


def print_profile(profile: Dict) -> None:
    """
    Pretty-print a data quality profile to stdout.

    Args:
        profile: Dictionary returned by profile_dataset().
    """
    name = profile["name"]
    shape = profile["shape"]

    print_section(f"DATASET: {name.upper()}")

    print(f"\n  Rows    : {shape['rows']:,}")
    print(f"  Columns : {shape['columns']}")
    print(f"  Duplicates : {profile['duplicate_count']:,}")

    # --- Data Types ---
    print_subsection("Column Data Types")
    ms = profile["missing_summary"]
    print(ms[["dtype", "missing_count", "missing_pct", "completeness_pct"]].to_string())

    # --- Missing Values ---
    print_subsection("Missing Value Summary")
    missing_cols = ms[ms["missing_count"] > 0]
    if missing_cols.empty:
        print("  No missing values detected.")
    else:
        print(missing_cols[["missing_count", "missing_pct"]].to_string())

    # --- Data Type Issues ---
    if profile["dtype_issues"]:
        print_subsection("Potential Data Type Issues (object cols storing numbers)")
        for col in profile["dtype_issues"]:
            print(f"  - {col}")

    # --- Columns Below Completeness Threshold ---
    if profile["columns_below_threshold"]:
        print_subsection(f"Columns Below {MIN_COMPLETENESS_THRESHOLD}% Completeness")
        for col in profile["columns_below_threshold"]:
            print(f"  - {col}")

    # --- Outlier Summary ---
    if profile["outlier_info"]:
        print_subsection("Outlier Summary (IQR Method)")
        rows = []
        for col, info in profile["outlier_info"].items():
            rows.append({
                "column": col,
                "outlier_count": info["outlier_count"],
                "outlier_pct": info["outlier_pct"],
                "lower_fence": info["lower_fence"],
                "upper_fence": info["upper_fence"],
            })
        outlier_df = pd.DataFrame(rows).set_index("column")
        print(outlier_df.to_string())

    # --- Basic Statistics ---
    print_subsection("Basic Statistics")
    if not profile["basic_stats"].empty:
        # Show only numeric describe to keep output clean
        numeric_stats = profile["basic_stats"].select_dtypes(include=[np.number])
        if not numeric_stats.empty:
            print(numeric_stats.to_string())
        else:
            print(profile["basic_stats"].to_string())
    else:
        print("  No statistics available.")


# ---------------------------------------------------------------------------
# Data Quality Report Generation
# ---------------------------------------------------------------------------

def build_quality_report(
    profiles: Dict[str, Dict],
    nav_df: Optional[pd.DataFrame] = None,
    fund_master_df: Optional[pd.DataFrame] = None,
) -> str:
    """
    Build a Markdown data quality report from profiling results.

    Args:
        profiles       : Dict of {dataset_name: profile_dict}.
        nav_df         : Optional combined NAV DataFrame for scheme validation.
        fund_master_df : Optional fund master DataFrame.

    Returns:
        Markdown string.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = [
        "# Data Quality Summary Report",
        "",
        f"**Generated:** {now}  ",
        f"**Pipeline:** data_ingestion.py v1.0.0  ",
        "**Project:** Bluestock Fintech — Mutual Fund Analytics  ",
        "",
        "---",
        "",
    ]

    for name, profile in profiles.items():
        shape = profile["shape"]
        ms = profile["missing_summary"]
        missing_cols = ms[ms["missing_count"] > 0]

        lines += [
            f"## Dataset: `{name}`",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Rows | {shape['rows']:,} |",
            f"| Total Columns | {shape['columns']} |",
            f"| Duplicate Rows | {profile['duplicate_count']:,} |",
            f"| Numeric Columns | {len(profile['numeric_columns'])} |",
            f"| Object Columns | {len(profile['object_columns'])} |",
            f"| Datetime Columns | {len(profile['datetime_columns'])} |",
            "",
        ]

        # Missing values table
        lines.append("### Missing Values")
        lines.append("")
        if missing_cols.empty:
            lines.append("No missing values detected. Dataset is complete.")
        else:
            lines.append("| Column | Missing Count | Missing % | Completeness % |")
            lines.append("|--------|--------------|-----------|----------------|")
            for col, row in missing_cols.iterrows():
                lines.append(
                    f"| {col} | {int(row['missing_count']):,} "
                    f"| {row['missing_pct']:.2f}% | {row['completeness_pct']:.2f}% |"
                )
        lines.append("")

        # Dtype issues
        lines.append("### Data Type Issues")
        lines.append("")
        if profile["dtype_issues"]:
            lines.append("| Column | Issue |")
            lines.append("|--------|-------|")
            for col in profile["dtype_issues"]:
                lines.append(f"| {col} | Stored as `object`, likely numeric |")
        else:
            lines.append("No data type issues detected.")
        lines.append("")

        # Outliers
        lines.append("### Outlier Detection (IQR Method)")
        lines.append("")
        if profile["outlier_info"]:
            lines.append("| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |")
            lines.append("|--------|--------------|-----------|-------------|-------------|")
            for col, info in profile["outlier_info"].items():
                lines.append(
                    f"| {col} | {info['outlier_count']:,} | {info['outlier_pct']:.2f}% "
                    f"| {info['lower_fence']} | {info['upper_fence']} |"
                )
        else:
            lines.append("No numeric columns available for outlier analysis.")
        lines.append("")

        lines.append("---")
        lines.append("")

    # --- AMFI Scheme Code Validation ---
    if nav_df is not None and fund_master_df is not None:
        lines += _build_scheme_validation_section(nav_df, fund_master_df)

    # --- Summary ---
    total_datasets = len(profiles)
    total_rows = sum(p["shape"]["rows"] for p in profiles.values())
    total_missing = sum(
        int(p["missing_summary"]["missing_count"].sum()) for p in profiles.values()
    )
    total_dupes = sum(p["duplicate_count"] for p in profiles.values())

    lines += [
        "## Overall Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Datasets Profiled | {total_datasets} |",
        f"| Total Records | {total_rows:,} |",
        f"| Total Missing Values | {total_missing:,} |",
        f"| Total Duplicate Rows | {total_dupes:,} |",
        "",
    ]

    return "\n".join(lines)


def _build_scheme_validation_section(
    nav_df: pd.DataFrame, fund_master_df: pd.DataFrame
) -> List[str]:
    """
    Validate that AMFI scheme codes in fund_master exist in nav_history.

    Args:
        nav_df         : NAV history DataFrame (must have 'scheme_code' column).
        fund_master_df : Fund master DataFrame (must have 'scheme_code' column).

    Returns:
        List of Markdown lines.
    """
    lines: List[str] = [
        "## AMFI Scheme Code Validation",
        "",
    ]

    nav_col = "scheme_code"
    master_col = "scheme_code"

    # Normalise column name lookup
    nav_cols_lower = {c.lower(): c for c in nav_df.columns}
    master_cols_lower = {c.lower(): c for c in fund_master_df.columns}

    nav_actual = nav_cols_lower.get("scheme_code") or nav_cols_lower.get("schemecode")
    master_actual = master_cols_lower.get("scheme_code") or master_cols_lower.get("schemecode")

    if nav_actual is None or master_actual is None:
        lines.append(
            "> `scheme_code` column not found in one or both datasets — "
            "skipping scheme validation."
        )
        lines.append("")
        return lines

    nav_codes = set(nav_df[nav_actual].dropna().astype(str).unique())
    master_codes = set(fund_master_df[master_actual].dropna().astype(str).unique())

    missing_in_nav = master_codes - nav_codes
    duplicates_in_master = (
        fund_master_df[master_actual]
        .dropna()
        .astype(str)
        .value_counts()
    )
    duplicate_codes = duplicates_in_master[duplicates_in_master > 1]

    lines += [
        f"| Check | Result |",
        f"|-------|--------|",
        f"| Scheme codes in fund_master | {len(master_codes):,} |",
        f"| Scheme codes in nav_history | {len(nav_codes):,} |",
        f"| Missing from nav_history | {len(missing_in_nav):,} |",
        f"| Duplicate codes in fund_master | {len(duplicate_codes):,} |",
        "",
    ]

    if missing_in_nav:
        lines.append("### Scheme Codes Missing from NAV History")
        lines.append("")
        lines.append("| Scheme Code |")
        lines.append("|-------------|")
        for code in sorted(missing_in_nav):
            lines.append(f"| {code} |")
        lines.append("")

    if not duplicate_codes.empty:
        lines.append("### Duplicate Scheme Codes in Fund Master")
        lines.append("")
        lines.append("| Scheme Code | Count |")
        lines.append("|-------------|-------|")
        for code, count in duplicate_codes.items():
            lines.append(f"| {code} | {count} |")
        lines.append("")

    return lines


def save_report(report_text: str, filename: str = "data_quality_summary.md") -> Path:
    """
    Save the data quality report to the reports directory.

    Args:
        report_text : Markdown string.
        filename    : Output filename.

    Returns:
        Path to the saved report file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / filename
    output_path.write_text(report_text, encoding="utf-8")
    logger.info("Data quality report saved to '%s'.", output_path)
    return output_path


def save_profiling_json(profiles: Dict[str, Dict], filename: str = "profiling_results.json") -> Path:
    """
    Serialize profiling metadata (excluding DataFrames) to JSON.

    Args:
        profiles : Dict of profiling results.
        filename : Output JSON filename.

    Returns:
        Path to the saved JSON file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / filename

    serialisable: Dict[str, Dict] = {}
    for name, profile in profiles.items():
        serialisable[name] = {
            "name": profile["name"],
            "shape": profile["shape"],
            "duplicate_count": profile["duplicate_count"],
            "numeric_columns": profile["numeric_columns"],
            "object_columns": profile["object_columns"],
            "datetime_columns": profile["datetime_columns"],
            "dtype_issues": profile["dtype_issues"],
            "columns_below_threshold": profile["columns_below_threshold"],
            "outlier_info": profile["outlier_info"],
            "missing_summary": {
                col: {
                    "missing_count": int(row["missing_count"]),
                    "missing_pct": float(row["missing_pct"]),
                    "completeness_pct": float(row["completeness_pct"]),
                    "dtype": str(row["dtype"]),
                }
                for col, row in profile["missing_summary"].iterrows()
            },
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serialisable, f, indent=2, default=str)

    logger.info("Profiling JSON saved to '%s'.", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Fund Master & NAV Analysis
# ---------------------------------------------------------------------------

def analyse_fund_master(df: pd.DataFrame) -> None:
    """
    Print exploratory analysis of the fund master dataset.

    Args:
        df: Fund master DataFrame.
    """
    print_section("FUND MASTER ANALYSIS")

    categorical_cols = [
        "fund_house", "scheme_type", "scheme_category",
        "scheme_sub_category", "risk_grade",
        # alternative naming conventions
        "amc", "category", "sub_category",
    ]

    for col in categorical_cols:
        # Case-insensitive match
        matched = [c for c in df.columns if c.lower() == col.lower()]
        if matched:
            actual_col = matched[0]
            counts = df[actual_col].value_counts()
            print(f"\n  [{actual_col}] — {counts.shape[0]} unique values")
            print(counts.to_string())


def analyse_nav_history(df: pd.DataFrame) -> None:
    """
    Print exploratory analysis of the NAV history dataset.

    Args:
        df: NAV history DataFrame.
    """
    print_section("NAV HISTORY ANALYSIS")

    print(f"\n  Total records : {len(df):,}")
    print(f"  Columns       : {list(df.columns)}")

    nav_col = next(
        (c for c in df.columns if c.lower() in {"nav", "net_asset_value", "nav_value"}),
        None,
    )
    date_col = next(
        (c for c in df.columns if c.lower() in {"date", "nav_date", "as_on_date"}),
        None,
    )
    scheme_col = next(
        (c for c in df.columns if c.lower() in {"scheme_code", "schemecode"}),
        None,
    )

    if scheme_col:
        print(f"\n  Unique schemes : {df[scheme_col].nunique()}")

    if nav_col:
        nav_series = pd.to_numeric(df[nav_col], errors="coerce").dropna()
        print(f"\n  NAV Statistics:")
        print(f"    Min    : ₹{nav_series.min():,.4f}")
        print(f"    Max    : ₹{nav_series.max():,.4f}")
        print(f"    Mean   : ₹{nav_series.mean():,.4f}")
        print(f"    Median : ₹{nav_series.median():,.4f}")

    if date_col:
        try:
            dates = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce").dropna()
            print(f"\n  Date Range : {dates.min().date()} → {dates.max().date()}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
    """
    Main entry point for the data ingestion pipeline.

    Execution flow:
        1. Discover and load all CSV files from data/raw/
        2. Profile each dataset
        3. Print profiling summaries
        4. Run specialised analyses (fund master, NAV history)
        5. Generate and save the data quality report
        6. Save profiling JSON
    """
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("Data Ingestion Pipeline — START")
    logger.info("Project root : %s", PROJECT_ROOT)
    logger.info("Raw data dir : %s", RAW_DATA_DIR)
    logger.info("=" * 70)

    # Step 1 — Load datasets
    try:
        datasets = load_all_datasets(RAW_DATA_DIR)
    except FileNotFoundError as exc:
        logger.error("Cannot start pipeline: %s", exc)
        sys.exit(1)

    if not datasets:
        logger.warning(
            "No CSV files found in '%s'. "
            "Run live_nav_fetch.py first to download data.",
            RAW_DATA_DIR,
        )
        # Still generate an empty report
        save_report("# Data Quality Summary\n\nNo datasets found.", "data_quality_summary.md")
        return

    # Step 2 — Profile datasets
    profiles: Dict[str, Dict] = {}
    for name, df in datasets.items():
        profiles[name] = profile_dataset(name, df)

    # Step 3 — Print profiles
    for profile in profiles.values():
        print_profile(profile)

    # Step 4 — Specialised analysis
    # Look for fund master and NAV history datasets by common naming patterns
    nav_df: Optional[pd.DataFrame] = None
    fund_master_df: Optional[pd.DataFrame] = None

    for name, df in datasets.items():
        name_lower = name.lower()
        if any(kw in name_lower for kw in ["nav", "all_funds", "hdfc"]):
            nav_df = df if nav_df is None else pd.concat([nav_df, df], ignore_index=True)
        if any(kw in name_lower for kw in ["fund_master", "master", "amfi"]):
            fund_master_df = df

    if nav_df is not None:
        analyse_nav_history(nav_df)

    if fund_master_df is not None:
        analyse_fund_master(fund_master_df)

    # Step 5 — Build & save data quality report
    report_text = build_quality_report(profiles, nav_df, fund_master_df)
    report_path = save_report(report_text)
    profiling_path = save_profiling_json(profiles)

    # Step 6 — Final summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print_section("PIPELINE COMPLETE")
    print(f"\n  Datasets processed : {len(datasets)}")
    print(f"  Report saved to    : {report_path}")
    print(f"  Profiling JSON     : {profiling_path}")
    print(f"  Elapsed time       : {elapsed:.2f}s")
    print()

    logger.info(
        "Pipeline completed successfully in %.2fs. Report: %s",
        elapsed,
        report_path,
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_pipeline()
