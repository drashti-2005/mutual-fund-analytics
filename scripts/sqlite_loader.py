"""
sqlite_loader.py
================
Loads all cleaned datasets into a SQLite star-schema database.

Day 2 — Bluestock Fintech Internship
Author  : Data Engineering Team
Date    : 2026-06-24
Version : 1.0.0

Description:
    Reads cleaned CSVs from data/processed/, builds dimension and fact tables,
    and loads them into bluestock_mf.db via SQLAlchemy. Verifies row counts
    and generates a loading report.

Usage:
    python scripts/sqlite_loader.py
"""

# ---------------------------------------------------------------------------
# Standard Library
# ---------------------------------------------------------------------------
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Third-Party
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text, inspect

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parent.parent
PROCESSED_DIR  = PROJECT_ROOT / "data" / "processed"
DB_DIR         = PROJECT_ROOT / "data" / "db"
DB_PATH        = DB_DIR / "bluestock_mf.db"
SCHEMA_FILE    = PROJECT_ROOT / "sql" / "schema.sql"
REPORTS_DIR    = PROJECT_ROOT / "reports"
LOG_DIR        = PROJECT_ROOT / "logs"
LOG_FILE       = LOG_DIR / "sqlite_loader.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-8s | %(funcName)-35s | %(message)s"
    logger = logging.getLogger("sqlite_loader")
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


def get_engine():
    """Create and return a SQLAlchemy engine for the SQLite database."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    logger.info("Connected to SQLite DB: %s", DB_PATH)
    return engine


def execute_schema(engine, schema_path: Path) -> None:
    """Execute the schema.sql DDL to create all tables."""
    if not schema_path.exists():
        logger.warning("schema.sql not found at %s — skipping DDL.", schema_path)
        return
    sql = schema_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                logger.debug("DDL skipped: %s", exc)
        conn.commit()
    logger.info("Schema applied from '%s'.", schema_path)


def load_table(
    engine,
    df: pd.DataFrame,
    table_name: str,
    if_exists: str = "replace",
    index: bool = False,
) -> int:
    """Load a DataFrame into a SQLite table. Returns rows loaded."""
    df.to_sql(table_name, engine, if_exists=if_exists, index=index)
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    logger.info("Table '%s': %d rows loaded.", table_name, count)
    return count


def verify_counts(engine, source_counts: Dict[str, int]) -> List[str]:
    """Compare source DataFrame row counts vs database row counts."""
    results = []
    insp = inspect(engine)
    tables = insp.get_table_names()
    for table, src_count in source_counts.items():
        if table not in tables:
            results.append(f"  ⚠  {table}: NOT FOUND in database")
            continue
        with engine.connect() as conn:
            db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        status = "✓" if db_count == src_count else "✗"
        results.append(
            f"  {status}  {table}: source={src_count:,} | db={db_count:,}"
        )
    return results


# ---------------------------------------------------------------------------
# Dimension Builders
# ---------------------------------------------------------------------------

def build_dim_fund(fund_master_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_fund from cleaned fund_master."""
    cols = [
        "amfi_code", "fund_house", "scheme_name", "category",
        "sub_category", "plan", "benchmark", "expense_ratio_pct",
        "exit_load_pct", "fund_manager", "risk_category",
    ]
    available = [c for c in cols if c in fund_master_df.columns]
    df = fund_master_df[available].drop_duplicates(subset=["amfi_code"])
    df["amfi_code"] = df["amfi_code"].astype(str)
    logger.info("dim_fund built — %d rows.", len(df))
    return df


def build_dim_date(nav_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build dim_date from the full NAV date range.
    Covers every calendar date from min to max NAV date.
    """
    min_date = nav_df["date"].min()
    max_date = nav_df["date"].max()
    dates = pd.date_range(start=min_date, end=max_date, freq="D")
    df = pd.DataFrame({"date": dates})
    df["year"]       = df["date"].dt.year
    df["month"]      = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%B")
    df["quarter"]    = df["date"].dt.quarter
    df["day_of_week"]= df["date"].dt.dayofweek          # 0=Mon
    df["day_name"]   = df["date"].dt.strftime("%A")
    df["is_weekday"] = df["day_of_week"].lt(5).astype(int)
    df["date"]       = df["date"].dt.strftime("%Y-%m-%d")
    logger.info("dim_date built — %d rows (%s → %s).", len(df), min_date.date(), max_date.date())
    return df


# ---------------------------------------------------------------------------
# Fact Builders
# ---------------------------------------------------------------------------

def build_fact_nav(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Build fact_nav — one row per (amfi_code, date)."""
    cols = ["amfi_code", "date", "nav", "daily_return_pct"]
    available = [c for c in cols if c in nav_df.columns]
    df = nav_df[available].copy()
    df["amfi_code"] = df["amfi_code"].astype(str)
    df["date"]      = df["date"].dt.strftime("%Y-%m-%d") if hasattr(df["date"].dt, "strftime") else df["date"].astype(str)
    df["nav"]       = df["nav"].round(4)
    logger.info("fact_nav built — %d rows.", len(df))
    return df


def build_fact_transactions(txn_df: pd.DataFrame) -> pd.DataFrame:
    """Build fact_transactions from cleaned investor_transactions."""
    cols = [
        "investor_id", "transaction_date", "amfi_code",
        "transaction_type", "amount_inr", "state", "city",
        "city_tier", "age_group", "gender", "annual_income_lakh",
        "payment_mode", "kyc_status",
    ]
    available = [c for c in cols if c in txn_df.columns]
    df = txn_df[available].copy()
    df["amfi_code"] = df["amfi_code"].astype(str)
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")
    logger.info("fact_transactions built — %d rows.", len(df))
    return df


def build_fact_performance(perf_df: pd.DataFrame) -> pd.DataFrame:
    """Build fact_performance from cleaned scheme_performance."""
    cols = [
        "amfi_code", "scheme_name", "fund_house", "category",
        "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
        "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
        "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
        "aum_crore", "expense_ratio_pct", "morningstar_rating", "risk_grade",
    ]
    available = [c for c in cols if c in perf_df.columns]
    df = perf_df[available].copy()
    df["amfi_code"] = df["amfi_code"].astype(str)
    logger.info("fact_performance built — %d rows.", len(df))
    return df


def build_fact_aum(aum_df: pd.DataFrame) -> pd.DataFrame:
    """Build fact_aum from cleaned aum_by_fund_house."""
    df = aum_df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    logger.info("fact_aum built — %d rows.", len(df))
    return df


def build_fact_portfolio(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """Build fact_portfolio from cleaned portfolio_holdings."""
    df = portfolio_df.copy()
    df["amfi_code"] = df["amfi_code"].astype(str)
    if "portfolio_date" in df.columns:
        df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    logger.info("fact_portfolio built — %d rows.", len(df))
    return df


# ---------------------------------------------------------------------------
# Loading Report
# ---------------------------------------------------------------------------

def build_loading_report(
    source_counts: Dict[str, int],
    verification: List[str],
    elapsed: float,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Database Loading Report — Day 2",
        "",
        f"**Generated:** {now}  ",
        f"**Database:** bluestock_mf.db  ",
        "**Project:** Bluestock Fintech — Mutual Fund Analytics  ",
        "",
        "---",
        "",
        "## Tables Loaded",
        "",
        "| Table | Rows Loaded |",
        "|-------|------------|",
    ]
    for table, count in source_counts.items():
        lines.append(f"| {table} | {count:,} |")

    lines += [
        "",
        "## Row Count Verification",
        "",
        "```",
    ] + verification + [
        "```",
        "",
        f"**Elapsed time:** {elapsed:.2f}s",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
    start = datetime.now()
    logger.info("=" * 70)
    logger.info("SQLite Loader Pipeline — START")
    logger.info("Database: %s", DB_PATH)
    logger.info("=" * 70)

    engine = get_engine()

    # Apply schema DDL
    execute_schema(engine, SCHEMA_FILE)

    source_counts: Dict[str, int] = {}

    # --- Load cleaned CSVs ---
    def read(filename: str) -> Optional[pd.DataFrame]:
        p = PROCESSED_DIR / filename
        if not p.exists():
            logger.warning("Processed file not found: %s", filename)
            return None
        return pd.read_csv(p, low_memory=False)

    # dim_fund
    print_section("Loading: dim_fund")
    fm = read("01_fund_master_clean.csv")
    if fm is not None:
        dim_fund = build_dim_fund(fm)
        n = load_table(engine, dim_fund, "dim_fund")
        source_counts["dim_fund"] = n

    # dim_date + fact_nav
    print_section("Loading: dim_date + fact_nav")
    nav = read("02_nav_history_clean.csv")
    if nav is not None:
        nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
        dim_date = build_dim_date(nav)
        n = load_table(engine, dim_date, "dim_date")
        source_counts["dim_date"] = n

        fact_nav = build_fact_nav(nav)
        n = load_table(engine, fact_nav, "fact_nav")
        source_counts["fact_nav"] = n

    # fact_transactions
    print_section("Loading: fact_transactions")
    txn = read("08_investor_transactions_clean.csv")
    if txn is not None:
        txn["transaction_date"] = pd.to_datetime(txn["transaction_date"], errors="coerce")
        fact_txn = build_fact_transactions(txn)
        n = load_table(engine, fact_txn, "fact_transactions")
        source_counts["fact_transactions"] = n

    # fact_performance
    print_section("Loading: fact_performance")
    perf = read("07_scheme_performance_clean.csv")
    if perf is not None:
        fact_perf = build_fact_performance(perf)
        n = load_table(engine, fact_perf, "fact_performance")
        source_counts["fact_performance"] = n

    # fact_aum
    print_section("Loading: fact_aum")
    aum = read("03_aum_by_fund_house_clean.csv")
    if aum is not None:
        fact_aum = build_fact_aum(aum)
        n = load_table(engine, fact_aum, "fact_aum")
        source_counts["fact_aum"] = n

    # fact_portfolio
    print_section("Loading: fact_portfolio")
    port = read("09_portfolio_holdings_clean.csv")
    if port is not None:
        fact_port = build_fact_portfolio(port)
        n = load_table(engine, fact_port, "fact_portfolio")
        source_counts["fact_portfolio"] = n

    # Additional supporting tables
    for raw_clean, table in [
        ("04_monthly_sip_inflows_clean.csv",  "fact_sip_inflows"),
        ("05_category_inflows_clean.csv",     "fact_category_inflows"),
        ("06_industry_folio_count_clean.csv", "fact_folio_count"),
        ("10_benchmark_indices_clean.csv",    "fact_benchmark"),
    ]:
        df = read(raw_clean)
        if df is not None:
            n = load_table(engine, df, table)
            source_counts[table] = n

    # --- Verify row counts ---
    print_section("Row Count Verification")
    verification = verify_counts(engine, source_counts)
    for line in verification:
        print(line)

    # --- Build loading report ---
    elapsed = (datetime.now() - start).total_seconds()
    report = build_loading_report(source_counts, verification, elapsed)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "db_loading_report.md"
    report_path.write_text(report, encoding="utf-8")

    print_section("LOADER PIPELINE COMPLETE")
    print(f"\n  Tables loaded : {len(source_counts)}")
    print(f"  Database      : {DB_PATH}")
    print(f"  Loading report: {report_path}")
    print(f"  Elapsed time  : {elapsed:.2f}s\n")
    logger.info("Loader pipeline completed in %.2fs.", elapsed)


if __name__ == "__main__":
    run_pipeline()
