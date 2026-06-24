-- =============================================================================
-- schema.sql
-- =============================================================================
-- Star Schema for Bluestock Fintech — Mutual Fund Analytics Platform
-- Day 2 — Data Engineering Internship
-- Author  : Data Engineering Team
-- Date    : 2026-06-24
-- DB      : SQLite (bluestock_mf.db)
--
-- Schema Overview (Star Schema):
--   Dimensions : dim_fund, dim_date
--   Facts      : fact_nav, fact_transactions, fact_performance,
--                fact_aum, fact_portfolio, fact_sip_inflows,
--                fact_category_inflows, fact_folio_count, fact_benchmark
-- =============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- DIMENSION: dim_fund
-- Master list of 40 mutual fund schemes (AMFI codes, metadata)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code          TEXT    PRIMARY KEY,   -- AMFI unique scheme identifier
    fund_house         TEXT    NOT NULL,      -- AMC name (e.g. SBI Mutual Fund)
    scheme_name        TEXT    NOT NULL,      -- Full official scheme name
    category           TEXT,                 -- Equity / Debt / Hybrid
    sub_category       TEXT,                 -- Large Cap / Mid Cap / Liquid etc.
    plan               TEXT,                 -- Regular / Direct
    benchmark          TEXT,                 -- Official benchmark index name
    expense_ratio_pct  REAL,                 -- Annual expense ratio in %
    exit_load_pct      REAL,                 -- Exit load percentage
    fund_manager       TEXT,                 -- Primary fund manager name
    risk_category      TEXT                  -- SEBI risk: Low/Moderate/High/Very High
);

-- ---------------------------------------------------------------------------
-- DIMENSION: dim_date
-- Calendar date dimension (full range from NAV history)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date        TEXT    PRIMARY KEY,  -- YYYY-MM-DD format
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,     -- 1-12
    month_name  TEXT    NOT NULL,     -- January ... December
    quarter     INTEGER NOT NULL,     -- 1-4
    day_of_week INTEGER NOT NULL,     -- 0=Monday, 6=Sunday
    day_name    TEXT    NOT NULL,     -- Monday ... Sunday
    is_weekday  INTEGER NOT NULL      -- 1=weekday, 0=weekend
);

-- ---------------------------------------------------------------------------
-- FACT: fact_nav
-- Daily NAV values for all schemes (one row per scheme per trading day)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_nav (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code        TEXT    NOT NULL REFERENCES dim_fund(amfi_code),
    date             TEXT    NOT NULL REFERENCES dim_date(date),
    nav              REAL    NOT NULL,   -- Net Asset Value in Rs.
    daily_return_pct REAL,               -- Day-over-day return %
    UNIQUE (amfi_code, date)
);

CREATE INDEX IF NOT EXISTS idx_fact_nav_amfi ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_fact_nav_date ON fact_nav(date);

-- ---------------------------------------------------------------------------
-- FACT: fact_transactions
-- Investor SIP / Lumpsum / Redemption transactions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_transactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id        TEXT    NOT NULL,
    transaction_date   TEXT    NOT NULL REFERENCES dim_date(date),
    amfi_code          TEXT    NOT NULL REFERENCES dim_fund(amfi_code),
    transaction_type   TEXT    NOT NULL CHECK(transaction_type IN ('SIP','Lumpsum','Redemption')),
    amount_inr         REAL    NOT NULL CHECK(amount_inr > 0),
    state              TEXT,
    city               TEXT,
    city_tier          TEXT    CHECK(city_tier IN ('T30','B30')),
    age_group          TEXT,
    gender             TEXT    CHECK(gender IN ('Male','Female')),
    annual_income_lakh REAL,
    payment_mode       TEXT,
    kyc_status         TEXT    CHECK(kyc_status IN ('Verified','Pending'))
);

CREATE INDEX IF NOT EXISTS idx_txn_amfi  ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_txn_date  ON fact_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_state ON fact_transactions(state);
CREATE INDEX IF NOT EXISTS idx_txn_type  ON fact_transactions(transaction_type);

-- ---------------------------------------------------------------------------
-- FACT: fact_performance
-- Risk-return metrics per scheme (as of latest available date)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_performance (
    amfi_code           TEXT    PRIMARY KEY REFERENCES dim_fund(amfi_code),
    scheme_name         TEXT,
    fund_house          TEXT,
    category            TEXT,
    return_1yr_pct      REAL,   -- 1-year absolute return %
    return_3yr_pct      REAL,   -- 3-year CAGR %
    return_5yr_pct      REAL,   -- 5-year CAGR %
    benchmark_3yr_pct   REAL,   -- Benchmark 3yr CAGR for comparison
    alpha               REAL,   -- Return above benchmark
    beta                REAL,   -- Market sensitivity (1.0 = same as market)
    sharpe_ratio        REAL,   -- Risk-adjusted return (higher is better)
    sortino_ratio       REAL,   -- Downside-risk-adjusted return
    std_dev_ann_pct     REAL,   -- Annualised standard deviation %
    max_drawdown_pct    REAL,   -- Worst peak-to-trough decline %
    aum_crore           REAL,   -- AUM in Rs. crore
    expense_ratio_pct   REAL,   -- Annual expense ratio %
    morningstar_rating  INTEGER CHECK(morningstar_rating BETWEEN 1 AND 5),
    risk_grade          TEXT
);

-- ---------------------------------------------------------------------------
-- FACT: fact_aum
-- Quarterly AUM per fund house
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_aum (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,   -- Quarter end date (YYYY-MM-DD)
    fund_house      TEXT    NOT NULL,
    aum_lakh_crore  REAL,               -- AUM in Rs. lakh crore
    aum_crore       REAL,               -- AUM in Rs. crore
    num_schemes     INTEGER,
    UNIQUE (date, fund_house)
);

-- ---------------------------------------------------------------------------
-- FACT: fact_portfolio
-- Top equity holdings per fund scheme
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_portfolio (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           TEXT    NOT NULL REFERENCES dim_fund(amfi_code),
    stock_symbol        TEXT    NOT NULL,
    stock_name          TEXT,
    sector              TEXT,
    weight_pct          REAL    CHECK(weight_pct >= 0 AND weight_pct <= 100),
    market_value_cr     REAL,
    current_price_inr   REAL,
    portfolio_date      TEXT
);

CREATE INDEX IF NOT EXISTS idx_portfolio_amfi   ON fact_portfolio(amfi_code);
CREATE INDEX IF NOT EXISTS idx_portfolio_sector ON fact_portfolio(sector);

-- ---------------------------------------------------------------------------
-- FACT: fact_sip_inflows
-- Monthly industry-wide SIP inflow statistics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sip_inflows (
    month                       TEXT    PRIMARY KEY,  -- YYYY-MM
    sip_inflow_crore            REAL,
    active_sip_accounts_crore   REAL,
    new_sip_accounts_lakh       REAL,
    sip_aum_lakh_crore          REAL,
    yoy_growth_pct              REAL
);

-- ---------------------------------------------------------------------------
-- FACT: fact_category_inflows
-- Monthly net inflows by fund category
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_category_inflows (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    month            TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    net_inflow_crore REAL,
    UNIQUE (month, category)
);

-- ---------------------------------------------------------------------------
-- FACT: fact_folio_count
-- Monthly industry folio count milestones
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_folio_count (
    month                TEXT    PRIMARY KEY,
    total_folios_crore   REAL,
    equity_folios_crore  REAL,
    debt_folios_crore    REAL,
    hybrid_folios_crore  REAL,
    others_folios_crore  REAL
);

-- ---------------------------------------------------------------------------
-- FACT: fact_benchmark
-- Daily closing values for benchmark indices
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_benchmark (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL REFERENCES dim_date(date),
    index_name  TEXT    NOT NULL,
    close_value REAL    NOT NULL,
    UNIQUE (date, index_name)
);

CREATE INDEX IF NOT EXISTS idx_benchmark_date  ON fact_benchmark(date);
CREATE INDEX IF NOT EXISTS idx_benchmark_index ON fact_benchmark(index_name);
