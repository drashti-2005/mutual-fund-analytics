"""
live_nav_fetch.py
=================
Live NAV data fetcher for Indian mutual funds via MFAPI.in.

Day 1 — Bluestock Fintech Internship
Author  : Data Engineering Team
Date    : 2026-06-22
Version : 1.0.0

Description:
    Fetches real-time NAV (Net Asset Value) history from the public MFAPI.in
    REST API for a configurable list of AMFI scheme codes. Data is saved as
    individual CSVs and combined into a master dataset.

API:
    GET https://api.mfapi.in/mf/{scheme_code}

Usage:
    python scripts/live_nav_fetch.py
"""

# ---------------------------------------------------------------------------
# Standard Library Imports
# ---------------------------------------------------------------------------
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Third-Party Imports
# ---------------------------------------------------------------------------
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# CONFIGURATION — Edit these variables as needed
# ---------------------------------------------------------------------------

# Project root is one level up from this script
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "live_nav_fetch.log"

# MFAPI base URL
MFAPI_BASE_URL = "https://api.mfapi.in/mf"

# Primary scheme (HDFC Top 100)
PRIMARY_SCHEME_CODE = 125497
PRIMARY_OUTPUT_FILE = RAW_DATA_DIR / "hdfc_top100_nav.csv"

# All schemes to download
SCHEME_CODES: Dict[int, str] = {
    119551: "SBI_Bluechip",
    120503: "ICICI_Bluechip",
    118632: "Nippon_LargeCap",
    119092: "Axis_Bluechip",
    120841: "Kotak_Bluechip",
    125497: "HDFC_Top100",
}

MASTER_OUTPUT_FILE = RAW_DATA_DIR / "all_funds_nav.csv"

# HTTP request configuration
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 1.5          # seconds; exponential back-off
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
INTER_REQUEST_DELAY_SECONDS = 0.5   # polite delay between API calls

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure and return a logger with console + file handlers."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(funcName)-28s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger("live_nav_fetch")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(ch)

    # File
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(fh)

    return logger


logger = setup_logging()

# ---------------------------------------------------------------------------
# HTTP Session with Retry
# ---------------------------------------------------------------------------

def build_http_session() -> requests.Session:
    """
    Build a requests Session with exponential back-off retry logic.

    Returns:
        Configured requests.Session instance.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=MAX_RETRY_ATTEMPTS,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Identify the client in the User-Agent header
    session.headers.update({
        "User-Agent": "BluestockMutualFundAnalytics/1.0 (internship-project)",
        "Accept": "application/json",
    })

    logger.debug(
        "HTTP session configured: retries=%d, backoff=%.1fs.",
        MAX_RETRY_ATTEMPTS,
        RETRY_BACKOFF_FACTOR,
    )
    return session


# ---------------------------------------------------------------------------
# API Interaction
# ---------------------------------------------------------------------------

def fetch_scheme_data(
    session: requests.Session,
    scheme_code: int,
) -> Optional[Dict]:
    """
    Fetch raw JSON data for a single mutual fund scheme from MFAPI.in.

    Args:
        session     : Configured requests Session.
        scheme_code : AMFI scheme code (integer).

    Returns:
        Parsed JSON dict on success, None on failure.
    """
    url = f"{MFAPI_BASE_URL}/{scheme_code}"
    logger.info("Fetching scheme %d from %s", scheme_code, url)

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        logger.error("Connection error for scheme %d: %s", scheme_code, exc)
        return None
    except requests.exceptions.Timeout:
        logger.error("Request timed out for scheme %d.", scheme_code)
        return None
    except requests.exceptions.HTTPError as exc:
        logger.error(
            "HTTP %d error for scheme %d: %s",
            exc.response.status_code,
            scheme_code,
            exc,
        )
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Unexpected request error for scheme %d: %s", scheme_code, exc)
        return None

    return _parse_json_response(response, scheme_code)


def _parse_json_response(
    response: requests.Response, scheme_code: int
) -> Optional[Dict]:
    """
    Safely parse and validate the JSON response from MFAPI.

    Args:
        response    : HTTP response object.
        scheme_code : AMFI scheme code (for logging).

    Returns:
        Validated JSON dict or None.
    """
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(
            "Failed to decode JSON for scheme %d: %s", scheme_code, exc
        )
        return None

    if not isinstance(data, dict):
        logger.error(
            "Unexpected JSON type for scheme %d: expected dict, got %s.",
            scheme_code,
            type(data).__name__,
        )
        return None

    status = data.get("status", "").lower()
    if status != "success":
        logger.warning(
            "API status for scheme %d is '%s' (expected 'success').",
            scheme_code,
            status,
        )

    if "data" not in data or not data["data"]:
        logger.error("No NAV data returned for scheme %d.", scheme_code)
        return None

    logger.debug(
        "Parsed %d NAV records for scheme %d.",
        len(data["data"]),
        scheme_code,
    )
    return data


# ---------------------------------------------------------------------------
# Data Extraction & Transformation
# ---------------------------------------------------------------------------

def extract_scheme_info(raw_data: Dict, scheme_code: int) -> Dict:
    """
    Extract scheme metadata from the API response.

    Args:
        raw_data    : Parsed JSON dict from MFAPI.
        scheme_code : AMFI scheme code.

    Returns:
        Dictionary of scheme metadata fields.
    """
    meta = raw_data.get("meta", {})
    return {
        "scheme_code": scheme_code,
        "fund_house": meta.get("fund_house", ""),
        "scheme_type": meta.get("scheme_type", ""),
        "scheme_category": meta.get("scheme_category", ""),
        "scheme_code_api": meta.get("scheme_code", scheme_code),
        "scheme_name": meta.get("scheme_name", ""),
    }


def extract_nav_history(raw_data: Dict, scheme_code: int) -> pd.DataFrame:
    """
    Convert the NAV history list from the API response into a DataFrame.

    Args:
        raw_data    : Parsed JSON dict from MFAPI.
        scheme_code : AMFI scheme code (added as a column).

    Returns:
        DataFrame with columns: scheme_code, date, nav.
    """
    nav_records = raw_data.get("data", [])

    if not nav_records:
        logger.warning("Empty NAV data list for scheme %d.", scheme_code)
        return pd.DataFrame(columns=["scheme_code", "date", "nav"])

    df = pd.DataFrame(nav_records)

    # Rename MFAPI columns to standard names
    column_map = {
        "date": "date",
        "nav": "nav",
    }
    df.rename(columns=column_map, inplace=True)

    # Ensure required columns exist
    if "date" not in df.columns or "nav" not in df.columns:
        logger.error(
            "Expected columns 'date'/'nav' missing for scheme %d. Found: %s",
            scheme_code,
            df.columns.tolist(),
        )
        return pd.DataFrame(columns=["scheme_code", "date", "nav"])

    # Add scheme code
    df.insert(0, "scheme_code", scheme_code)

    # Parse date (MFAPI returns DD-MM-YYYY)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    # Parse NAV to float
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    # Drop rows where date or NAV could not be parsed
    invalid_mask = df["date"].isna() | df["nav"].isna()
    if invalid_mask.any():
        logger.warning(
            "Dropped %d invalid record(s) for scheme %d.",
            int(invalid_mask.sum()),
            scheme_code,
        )
        df = df[~invalid_mask].copy()

    # Sort chronologically
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info(
        "Extracted %d NAV records for scheme %d (range: %s → %s).",
        len(df),
        scheme_code,
        df["date"].min().date() if not df.empty else "N/A",
        df["date"].max().date() if not df.empty else "N/A",
    )
    return df


def enrich_nav_df(nav_df: pd.DataFrame, scheme_info: Dict) -> pd.DataFrame:
    """
    Enrich the NAV DataFrame with scheme metadata columns.

    Args:
        nav_df      : Raw NAV DataFrame from extract_nav_history().
        scheme_info : Metadata dict from extract_scheme_info().

    Returns:
        Enriched DataFrame.
    """
    for col in ("fund_house", "scheme_name", "scheme_category", "scheme_type"):
        if col in scheme_info:
            nav_df[col] = scheme_info[col]
    return nav_df


# ---------------------------------------------------------------------------
# Single-Scheme Download
# ---------------------------------------------------------------------------

def download_scheme_nav(
    session: requests.Session,
    scheme_code: int,
    friendly_name: str,
    output_path: Path,
) -> Optional[pd.DataFrame]:
    """
    Download, validate, parse, and save NAV data for one scheme.

    Args:
        session      : Configured requests Session.
        scheme_code  : AMFI scheme code.
        friendly_name: Human-readable fund name (used in file naming).
        output_path  : Absolute path to save the CSV.

    Returns:
        DataFrame on success, None on failure.
    """
    raw_data = fetch_scheme_data(session, scheme_code)
    if raw_data is None:
        logger.error("Skipping scheme %d (%s) — no data.", scheme_code, friendly_name)
        return None

    scheme_info = extract_scheme_info(raw_data, scheme_code)
    nav_df = extract_nav_history(raw_data, scheme_code)

    if nav_df.empty:
        logger.error("Empty NAV DataFrame for scheme %d (%s).", scheme_code, friendly_name)
        return None

    nav_df = enrich_nav_df(nav_df, scheme_info)

    # Save individual CSV
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    nav_df.to_csv(output_path, index=False)
    logger.info(
        "Saved %d records → '%s'.",
        len(nav_df),
        output_path.name,
    )

    # Print scheme details to console
    print(f"\n  Scheme : {scheme_info['scheme_name']}")
    print(f"  Code   : {scheme_code}")
    print(f"  House  : {scheme_info['fund_house']}")
    print(f"  Records: {len(nav_df):,}")
    print(f"  Date   : {nav_df['date'].min().date()} → {nav_df['date'].max().date()}")
    print(f"  File   : {output_path.name}")
    print(nav_df.head(5).to_string(index=False))

    return nav_df


# ---------------------------------------------------------------------------
# Batch Download
# ---------------------------------------------------------------------------

def download_all_schemes(
    scheme_codes: Dict[int, str],
) -> Tuple[List[pd.DataFrame], List[int]]:
    """
    Loop through all scheme codes, download NAV data, and save individual CSVs.

    Args:
        scheme_codes: Dict mapping AMFI code → friendly fund name.

    Returns:
        Tuple of (list_of_successful_dfs, list_of_failed_codes).
    """
    session = build_http_session()
    successful_dfs: List[pd.DataFrame] = []
    failed_codes: List[int] = []

    total = len(scheme_codes)
    for idx, (code, name) in enumerate(scheme_codes.items(), start=1):
        print(f"\n[{idx}/{total}] Fetching {name} (scheme: {code})...")
        logger.info("[%d/%d] Fetching %s (scheme: %d).", idx, total, name, code)

        output_file = RAW_DATA_DIR / f"{name.lower()}_nav.csv"
        df = download_scheme_nav(session, code, name, output_file)

        if df is not None:
            successful_dfs.append(df)
        else:
            failed_codes.append(code)

        # Polite delay to avoid hammering the public API
        if idx < total:
            time.sleep(INTER_REQUEST_DELAY_SECONDS)

    session.close()
    return successful_dfs, failed_codes


# ---------------------------------------------------------------------------
# Master Dataset Builder
# ---------------------------------------------------------------------------

def build_master_nav_dataset(
    dfs: List[pd.DataFrame], output_path: Path
) -> Optional[pd.DataFrame]:
    """
    Concatenate all individual NAV DataFrames into one master CSV.

    Args:
        dfs         : List of individual fund NAV DataFrames.
        output_path : Absolute path to save the combined CSV.

    Returns:
        Combined DataFrame or None if the list is empty.
    """
    if not dfs:
        logger.error("No data to combine — master NAV file not created.")
        return None

    master_df = pd.concat(dfs, ignore_index=True)
    master_df.sort_values(["scheme_code", "date"], inplace=True)
    master_df.reset_index(drop=True, inplace=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    master_df.to_csv(output_path, index=False)

    logger.info(
        "Master NAV dataset saved to '%s' — %d records across %d scheme(s).",
        output_path.name,
        len(master_df),
        master_df["scheme_code"].nunique(),
    )
    return master_df


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_api_response(raw_data: Optional[Dict], scheme_code: int) -> bool:
    """
    Validate key fields of the MFAPI JSON response.

    Args:
        raw_data    : Parsed JSON dict (may be None).
        scheme_code : AMFI code for logging.

    Returns:
        True if valid, False otherwise.
    """
    if raw_data is None:
        return False

    checks = {
        "has 'status' key": "status" in raw_data,
        "status is 'success'": raw_data.get("status", "").lower() == "success",
        "has 'meta' key": "meta" in raw_data,
        "has 'data' key": "data" in raw_data,
        "data is non-empty list": isinstance(raw_data.get("data"), list) and len(raw_data["data"]) > 0,
    }

    all_passed = True
    for check, result in checks.items():
        if not result:
            logger.warning("Validation FAIL for scheme %d — %s.", scheme_code, check)
            all_passed = False
        else:
            logger.debug("Validation PASS for scheme %d — %s.", scheme_code, check)

    return all_passed


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def run_nav_fetch() -> None:
    """
    Orchestrate the full NAV fetch pipeline:
        1. Download primary scheme (HDFC Top 100)
        2. Download all configured schemes
        3. Build and save master combined dataset
        4. Print summary statistics
    """
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("Live NAV Fetch Pipeline — START")
    logger.info("API Base URL : %s", MFAPI_BASE_URL)
    logger.info("Output Dir   : %s", RAW_DATA_DIR)
    logger.info("=" * 70)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Step 1 — Primary scheme: HDFC Top 100 Fund
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 70)
    print("  STEP 1: Fetching HDFC Top 100 Fund (Primary Scheme)")
    print("=" * 70)

    session = build_http_session()
    raw_primary = fetch_scheme_data(session, PRIMARY_SCHEME_CODE)

    if validate_api_response(raw_primary, PRIMARY_SCHEME_CODE):
        scheme_info = extract_scheme_info(raw_primary, PRIMARY_SCHEME_CODE)
        hdfc_df = extract_nav_history(raw_primary, PRIMARY_SCHEME_CODE)
        hdfc_df = enrich_nav_df(hdfc_df, scheme_info)
        hdfc_df.to_csv(PRIMARY_OUTPUT_FILE, index=False)
        logger.info(
            "HDFC Top 100 saved: %d records → %s",
            len(hdfc_df),
            PRIMARY_OUTPUT_FILE.name,
        )
        print(f"\n  Scheme Name : {scheme_info['scheme_name']}")
        print(f"  Fund House  : {scheme_info['fund_house']}")
        print(f"  Category    : {scheme_info['scheme_category']}")
        print(f"  Records     : {len(hdfc_df):,}")
        print(f"  Saved to    : {PRIMARY_OUTPUT_FILE}")
        print("\n  First 5 NAV records:")
        print(hdfc_df[["date", "nav"]].head(5).to_string(index=False))
        print("\n  Last 5 NAV records:")
        print(hdfc_df[["date", "nav"]].tail(5).to_string(index=False))
    else:
        logger.error("Primary scheme fetch failed — continuing with batch download.")

    session.close()

    # ------------------------------------------------------------------ #
    # Step 2 — Batch download all configured schemes
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 70)
    print("  STEP 2: Batch Downloading All Fund Schemes")
    print("=" * 70)

    successful_dfs, failed_codes = download_all_schemes(SCHEME_CODES)

    # ------------------------------------------------------------------ #
    # Step 3 — Build master NAV dataset
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 70)
    print("  STEP 3: Building Master NAV Dataset")
    print("=" * 70)

    master_df = build_master_nav_dataset(successful_dfs, MASTER_OUTPUT_FILE)

    # ------------------------------------------------------------------ #
    # Step 4 — Summary
    # ------------------------------------------------------------------ #
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("  NAV FETCH PIPELINE — SUMMARY")
    print("=" * 70)
    print(f"\n  Schemes requested  : {len(SCHEME_CODES)}")
    print(f"  Schemes downloaded : {len(successful_dfs)}")
    print(f"  Schemes failed     : {len(failed_codes)}")
    if failed_codes:
        print(f"  Failed codes       : {failed_codes}")
    if master_df is not None:
        print(f"  Master records     : {len(master_df):,}")
        print(f"  Master file        : {MASTER_OUTPUT_FILE}")
        print(f"\n  Master Dataset — Head:")
        print(master_df.head(5).to_string(index=False))
        print(f"\n  NAV Statistics by Scheme:")
        scheme_col = "scheme_code"
        nav_col = "nav"
        if scheme_col in master_df.columns and nav_col in master_df.columns:
            summary = master_df.groupby(scheme_col)[nav_col].agg(
                count="count",
                min_nav="min",
                max_nav="max",
                mean_nav="mean",
            ).round(4)
            print(summary.to_string())
    print(f"\n  Elapsed time       : {elapsed:.2f}s")
    print()

    logger.info(
        "Live NAV Fetch Pipeline completed in %.2fs. "
        "Success: %d, Failed: %d.",
        elapsed,
        len(successful_dfs),
        len(failed_codes),
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_nav_fetch()
