# Data Dictionary
## Bluestock Fintech — Mutual Fund Analytics Platform
**Day 2 | Version:** 1.0.0  
**Author:** Data Engineering Team  
**Date:** 2026-06-24  

---

## Table of Contents
1. [dim_fund](#dim_fund)
2. [dim_date](#dim_date)
3. [fact_nav](#fact_nav)
4. [fact_transactions](#fact_transactions)
5. [fact_performance](#fact_performance)
6. [fact_aum](#fact_aum)
7. [fact_portfolio](#fact_portfolio)
8. [fact_sip_inflows](#fact_sip_inflows)
9. [fact_category_inflows](#fact_category_inflows)
10. [fact_folio_count](#fact_folio_count)
11. [fact_benchmark](#fact_benchmark)

---

## dim_fund

**Source file:** `01_fund_master.csv`  
**Description:** Master dimension table of all 40 mutual fund schemes tracked in this project.  
**Rows:** ~40

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `amfi_code` | TEXT (PK) | AMFI unique scheme identifier | Primary key linking all fact tables | Not null, unique |
| `fund_house` | TEXT | Asset Management Company name | E.g. SBI Mutual Fund, HDFC Mutual Fund | Not null |
| `scheme_name` | TEXT | Full official AMFI scheme name | E.g. "SBI Bluechip Fund - Regular Plan - Growth" | Not null |
| `category` | TEXT | Broad fund category | Equity / Debt / Hybrid | Not null |
| `sub_category` | TEXT | SEBI sub-category | Large Cap / Mid Cap / Small Cap / Liquid / ELSS etc. | — |
| `plan` | TEXT | Plan type | Regular or Direct | In (Regular, Direct) |
| `benchmark` | TEXT | Official benchmark index | E.g. NIFTY 100 TRI | — |
| `expense_ratio_pct` | REAL | Annual expense ratio in % | Cost charged by AMC to investors annually | 0.1–2.5% |
| `exit_load_pct` | REAL | Exit load % on redemption | Penalty for early withdrawal (0% for liquid funds) | 0–3% |
| `fund_manager` | TEXT | Primary fund manager name | Person responsible for investment decisions | — |
| `risk_category` | TEXT | SEBI risk classification | Low / Moderate / High / Very High | SEBI enum |

---

## dim_date

**Source file:** Generated from NAV history date range  
**Description:** Calendar dimension table covering every date from Jan 2022 to Dec 2025.  
**Rows:** ~1,461

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `date` | TEXT (PK) | Calendar date in YYYY-MM-DD | Primary key for time-based joins | Not null, unique |
| `year` | INTEGER | Calendar year | E.g. 2022, 2023 | 2022–2026 |
| `month` | INTEGER | Month number | 1–12 | 1–12 |
| `month_name` | TEXT | Month name | January … December | Not null |
| `quarter` | INTEGER | Quarter number | Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec | 1–4 |
| `day_of_week` | INTEGER | Day of week (0=Monday) | Used for weekday/weekend analysis | 0–6 |
| `day_name` | TEXT | Day name | Monday … Sunday | Not null |
| `is_weekday` | INTEGER | Weekday flag | 1=weekday (markets open), 0=weekend | 0 or 1 |

---

## fact_nav

**Source file:** `02_nav_history.csv`  
**Description:** Daily NAV (Net Asset Value) for all 40 schemes from Jan 2022 to May 2026.  
**Rows:** ~46,000

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `id` | INTEGER (PK) | Auto-increment surrogate key | Unique row identifier | Not null |
| `amfi_code` | TEXT (FK) | Links to dim_fund | Which scheme this NAV belongs to | FK → dim_fund |
| `date` | TEXT (FK) | Links to dim_date | Trading day of the NAV | FK → dim_date |
| `nav` | REAL | Net Asset Value in Rs. | Price of one unit of the fund | > 0 |
| `daily_return_pct` | REAL | Day-over-day return % | (NAV_today / NAV_yesterday - 1) × 100 | Computed field |

---

## fact_transactions

**Source file:** `08_investor_transactions.csv`  
**Description:** ~32,000 investor transactions (SIP, Lumpsum, Redemption) across 5,000 investors.  
**Rows:** ~32,000

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `id` | INTEGER (PK) | Auto-increment surrogate key | Unique transaction identifier | Not null |
| `investor_id` | TEXT | Unique investor code | E.g. INV000001 | Not null |
| `transaction_date` | TEXT (FK) | Date of transaction | Links to dim_date | FK → dim_date |
| `amfi_code` | TEXT (FK) | Fund invested in | Links to dim_fund | FK → dim_fund |
| `transaction_type` | TEXT | Type of transaction | SIP / Lumpsum / Redemption | In enum |
| `amount_inr` | REAL | Transaction amount in Rs. | Investment or redemption value | > 0 |
| `state` | TEXT | Investor's Indian state | Geographic segmentation | 12 states |
| `city` | TEXT | Investor's city | City-level analysis | — |
| `city_tier` | TEXT | AMFI city classification | T30 (top 30 cities) / B30 (beyond top 30) | T30 or B30 |
| `age_group` | TEXT | Investor age bracket | 18-25 / 26-35 / 36-45 / 46-55 / 56+ | Age enum |
| `gender` | TEXT | Investor gender | Male / Female | In enum |
| `annual_income_lakh` | REAL | Annual income in Rs. lakh | Income-based segmentation | > 0 |
| `payment_mode` | TEXT | Mode of payment | UPI / Net Banking / Mandate / Cheque | — |
| `kyc_status` | TEXT | KYC verification status | Verified / Pending | In enum |

---

## fact_performance

**Source file:** `07_scheme_performance.csv`  
**Description:** Risk and return metrics per scheme computed from NAV history.  
**Rows:** 40

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `amfi_code` | TEXT (PK/FK) | AMFI scheme code | Links to dim_fund | FK → dim_fund |
| `return_1yr_pct` | REAL | 1-year absolute return % | Short-term performance | -100 to 200 |
| `return_3yr_pct` | REAL | 3-year CAGR % | Medium-term CAGR | -100 to 200 |
| `return_5yr_pct` | REAL | 5-year CAGR % | Long-term CAGR | -100 to 200 |
| `benchmark_3yr_pct` | REAL | Benchmark 3yr CAGR % | For alpha calculation | — |
| `alpha` | REAL | Return above benchmark | Positive = outperforming index | Computed |
| `beta` | REAL | Market sensitivity | 1.0 = moves with market, >1 = more volatile | > 0 |
| `sharpe_ratio` | REAL | Risk-adjusted return | (Return - Risk-free rate) / Std Dev; >1 is good | — |
| `sortino_ratio` | REAL | Downside risk-adjusted return | Like Sharpe but only penalises negative returns | — |
| `std_dev_ann_pct` | REAL | Annualised volatility % | Higher = more volatile fund | > 0 |
| `max_drawdown_pct` | REAL | Worst peak-to-trough % decline | Negative value; -20% means 20% fall from peak | < 0 |
| `aum_crore` | REAL | Assets Under Management (Rs. crore) | Fund size | > 0 |
| `expense_ratio_pct` | REAL | Annual expense ratio % | Cost to investor | 0.1–2.5 |
| `morningstar_rating` | INTEGER | Star rating | 1–5 stars based on risk-adjusted performance | 1–5 |
| `risk_grade` | TEXT | Risk classification | Low / Moderate / High / Very High | SEBI enum |

---

## fact_aum

**Source file:** `03_aum_by_fund_house.csv`  
**Description:** Quarterly AUM for 10 major fund houses from 2022 to 2025.  
**Rows:** ~90

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `id` | INTEGER (PK) | Surrogate key | Unique row identifier | Not null |
| `date` | TEXT | Quarter-end date (YYYY-MM-DD) | E.g. 2022-03-31 = Q4 FY22 | Valid date |
| `fund_house` | TEXT | AMC name | E.g. SBI Mutual Fund | Not null |
| `aum_lakh_crore` | REAL | AUM in Rs. lakh crore | Industry-scale AUM metric | > 0 |
| `aum_crore` | REAL | AUM in Rs. crore | Scheme-level AUM metric | > 0 |
| `num_schemes` | INTEGER | Number of schemes managed | Breadth of AMC offering | > 0 |

---

## fact_portfolio

**Source file:** `09_portfolio_holdings.csv`  
**Description:** Top equity stock holdings for each mutual fund as of Dec 2025.  
**Rows:** ~320

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `id` | INTEGER (PK) | Surrogate key | Unique row identifier | Not null |
| `amfi_code` | TEXT (FK) | Fund holding this stock | Links to dim_fund | FK → dim_fund |
| `stock_symbol` | TEXT | NSE/BSE ticker symbol | E.g. POWERGRID, RELIANCE | Not null |
| `stock_name` | TEXT | Company full name | E.g. Power Grid Corporation | — |
| `sector` | TEXT | Industry sector | E.g. Utilities, Financials | — |
| `weight_pct` | REAL | Portfolio weight % | Portion of fund AUM in this stock | 0–100 |
| `market_value_cr` | REAL | Market value in Rs. crore | Stock holding value in portfolio | > 0 |
| `current_price_inr` | REAL | Stock price in Rs. | Latest market price | > 0 |
| `portfolio_date` | TEXT | Disclosure date | Date of portfolio snapshot | Valid date |

---

## fact_sip_inflows

**Source file:** `04_monthly_sip_inflows.csv`  
**Description:** Monthly industry-wide SIP statistics from AMFI Monthly Notes.  
**Rows:** 48

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `month` | TEXT (PK) | Month in YYYY-MM format | E.g. 2025-12 | Not null |
| `sip_inflow_crore` | REAL | Total SIP inflows in Rs. crore | Industry SIP collection that month | > 0 |
| `active_sip_accounts_crore` | REAL | Active SIP account count (crore) | E.g. 9.35 crore in Dec 2025 | > 0 |
| `new_sip_accounts_lakh` | REAL | New SIP registrations (lakh) | Fresh SIP mandates registered | > 0 |
| `sip_aum_lakh_crore` | REAL | SIP AUM in Rs. lakh crore | Total assets via SIP route | > 0 |
| `yoy_growth_pct` | REAL | Year-over-year growth % | Measures adoption acceleration | Computed |

---

## fact_category_inflows

**Source file:** `05_category_inflows.csv`  
**Description:** Monthly net inflows by fund category for FY 2024-25.  
**Rows:** ~144

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `id` | INTEGER (PK) | Surrogate key | Unique row identifier | Not null |
| `month` | TEXT | Month in YYYY-MM | Time dimension | Not null |
| `category` | TEXT | Fund category | Large Cap / Mid Cap / ELSS / Liquid etc. | Not null |
| `net_inflow_crore` | REAL | Net inflow in Rs. crore | Purchases minus redemptions | Can be negative |

---

## fact_folio_count

**Source file:** `06_industry_folio_count.csv`  
**Description:** Monthly total mutual fund folios broken by Equity, Debt, Hybrid.  
**Rows:** 21

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `month` | TEXT (PK) | Month in YYYY-MM | Time dimension | Not null |
| `total_folios_crore` | REAL | Total folios (crore) | E.g. 26.12 crore in Dec 2025 | > 0 |
| `equity_folios_crore` | REAL | Equity scheme folios (crore) | Largest folio segment | > 0 |
| `debt_folios_crore` | REAL | Debt scheme folios (crore) | Fixed income investors | > 0 |
| `hybrid_folios_crore` | REAL | Hybrid scheme folios (crore) | Balanced fund investors | > 0 |
| `others_folios_crore` | REAL | Other scheme folios (crore) | Index, sectoral, etc. | ≥ 0 |

---

## fact_benchmark

**Source file:** `10_benchmark_indices.csv`  
**Description:** Daily closing values for Nifty 50, Nifty 100, Nifty Midcap 150, BSE SmallCap indices.  
**Rows:** ~8,000

| Column | Type | Description | Business Meaning | Validation |
|--------|------|-------------|-----------------|------------|
| `id` | INTEGER (PK) | Surrogate key | Unique row identifier | Not null |
| `date` | TEXT (FK) | Trading date | Links to dim_date | FK → dim_date |
| `index_name` | TEXT | Index identifier | NIFTY50 / NIFTY100 / etc. | Not null |
| `close_value` | REAL | Index closing value | Used to compute benchmark returns | > 0 |
