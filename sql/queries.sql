-- =============================================================================
-- queries.sql
-- =============================================================================
-- Analytical SQL Queries for Bluestock Fintech — Mutual Fund Analytics
-- Day 2 — Data Engineering Internship
-- Author  : Data Engineering Team
-- Date    : 2026-06-24
-- DB      : SQLite (bluestock_mf.db)
--
-- Query Index:
--   Q01  Top 5 funds by AUM
--   Q02  Average NAV per month (all schemes)
--   Q03  SIP inflow Year-over-Year growth
--   Q04  Total transaction amount by state
--   Q05  Funds with expense ratio < 1%
--   Q06  Top 5 highest 3-year return funds
--   Q07  Lowest risk funds by standard deviation
--   Q08  Fund house performance comparison (avg Sharpe)
--   Q09  Monthly SIP transaction volume trend
--   Q10  Top transaction categories by value
--   Q11  Funds outperforming their benchmark (alpha > 0)
--   Q12  Sector concentration in equity fund portfolios
--   Q13  Investor age group vs average SIP amount
--   Q14  T30 vs B30 city investment split
--   Q15  Best risk-adjusted funds (Sharpe > 1.0)
-- =============================================================================


-- ----------------------------------------------------------------------------
-- Q01: Top 5 Funds by AUM
-- Business use: Identify the largest funds by assets under management.
-- ----------------------------------------------------------------------------
SELECT
    fp.scheme_name,
    fp.fund_house,
    fp.category,
    ROUND(fp.aum_crore, 2)          AS aum_crore,
    fp.expense_ratio_pct,
    fp.risk_grade
FROM fact_performance fp
ORDER BY fp.aum_crore DESC
LIMIT 5;


-- ----------------------------------------------------------------------------
-- Q02: Average NAV Per Month (All Schemes Combined)
-- Business use: Track overall market NAV trend month-by-month.
-- ----------------------------------------------------------------------------
SELECT
    dd.year,
    dd.month,
    dd.month_name,
    ROUND(AVG(fn.nav), 4)           AS avg_nav,
    COUNT(DISTINCT fn.amfi_code)    AS active_schemes,
    COUNT(*)                        AS total_records
FROM fact_nav fn
JOIN dim_date dd ON fn.date = dd.date
GROUP BY dd.year, dd.month
ORDER BY dd.year, dd.month;


-- ----------------------------------------------------------------------------
-- Q03: SIP Inflow Year-over-Year Growth
-- Business use: Monitor SIP adoption momentum across years.
-- ----------------------------------------------------------------------------
SELECT
    SUBSTR(month, 1, 4)             AS year,
    ROUND(SUM(sip_inflow_crore), 2) AS total_sip_inflow_crore,
    ROUND(AVG(sip_inflow_crore), 2) AS avg_monthly_sip_crore,
    COUNT(*)                        AS months_reported
FROM fact_sip_inflows
GROUP BY SUBSTR(month, 1, 4)
ORDER BY year;


-- ----------------------------------------------------------------------------
-- Q04: Total Transaction Amount by State
-- Business use: Geographic distribution of investor activity.
-- ----------------------------------------------------------------------------
SELECT
    state,
    COUNT(*)                            AS total_transactions,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_amount_crore,
    ROUND(AVG(amount_inr), 2)          AS avg_transaction_inr,
    COUNT(DISTINCT investor_id)         AS unique_investors
FROM fact_transactions
WHERE state IS NOT NULL
GROUP BY state
ORDER BY total_amount_crore DESC;


-- ----------------------------------------------------------------------------
-- Q05: Funds with Expense Ratio < 1%
-- Business use: Identify cost-efficient fund options for investors.
-- ----------------------------------------------------------------------------
SELECT
    df.amfi_code,
    df.scheme_name,
    df.fund_house,
    df.category,
    df.sub_category,
    df.expense_ratio_pct,
    fp.return_3yr_pct,
    fp.sharpe_ratio
FROM dim_fund df
LEFT JOIN fact_performance fp ON df.amfi_code = fp.amfi_code
WHERE df.expense_ratio_pct < 1.0
ORDER BY df.expense_ratio_pct ASC;


-- ----------------------------------------------------------------------------
-- Q06: Top 5 Funds by 3-Year CAGR Return
-- Business use: Identify best performing funds over a 3-year horizon.
-- ----------------------------------------------------------------------------
SELECT
    fp.scheme_name,
    fp.fund_house,
    fp.category,
    ROUND(fp.return_3yr_pct, 2)     AS return_3yr_pct,
    ROUND(fp.benchmark_3yr_pct, 2)  AS benchmark_3yr_pct,
    ROUND(fp.alpha, 2)              AS alpha,
    fp.morningstar_rating
FROM fact_performance fp
WHERE fp.return_3yr_pct IS NOT NULL
ORDER BY fp.return_3yr_pct DESC
LIMIT 5;


-- ----------------------------------------------------------------------------
-- Q07: Lowest Risk Funds by Annualised Standard Deviation
-- Business use: Identify stable funds suitable for risk-averse investors.
-- ----------------------------------------------------------------------------
SELECT
    fp.scheme_name,
    fp.fund_house,
    fp.category,
    ROUND(fp.std_dev_ann_pct, 2)    AS std_dev_ann_pct,
    ROUND(fp.max_drawdown_pct, 2)   AS max_drawdown_pct,
    ROUND(fp.return_3yr_pct, 2)     AS return_3yr_pct,
    fp.risk_grade
FROM fact_performance fp
WHERE fp.std_dev_ann_pct IS NOT NULL
ORDER BY fp.std_dev_ann_pct ASC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Q08: Fund House Performance Comparison (Average Sharpe Ratio)
-- Business use: Compare which AMC consistently delivers risk-adjusted returns.
-- ----------------------------------------------------------------------------
SELECT
    fp.fund_house,
    COUNT(*)                            AS num_schemes,
    ROUND(AVG(fp.sharpe_ratio), 3)      AS avg_sharpe_ratio,
    ROUND(AVG(fp.return_3yr_pct), 2)    AS avg_return_3yr_pct,
    ROUND(AVG(fp.alpha), 3)             AS avg_alpha,
    ROUND(SUM(fp.aum_crore), 0)         AS total_aum_crore
FROM fact_performance fp
WHERE fp.fund_house IS NOT NULL
GROUP BY fp.fund_house
ORDER BY avg_sharpe_ratio DESC;


-- ----------------------------------------------------------------------------
-- Q09: Monthly SIP Transaction Volume Trend
-- Business use: Track growth in SIP transaction count and value over time.
-- ----------------------------------------------------------------------------
SELECT
    SUBSTR(transaction_date, 1, 7)          AS month,
    COUNT(*)                                AS sip_count,
    ROUND(SUM(amount_inr) / 1e7, 2)        AS total_amount_crore,
    ROUND(AVG(amount_inr), 2)              AS avg_sip_amount_inr
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY SUBSTR(transaction_date, 1, 7)
ORDER BY month;


-- ----------------------------------------------------------------------------
-- Q10: Top Transaction Categories by Total Value
-- Business use: Understand which transaction types drive most investment volume.
-- ----------------------------------------------------------------------------
SELECT
    transaction_type,
    COUNT(*)                            AS transaction_count,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_amount_crore,
    ROUND(AVG(amount_inr), 2)          AS avg_amount_inr,
    ROUND(
        100.0 * SUM(amount_inr) /
        SUM(SUM(amount_inr)) OVER (), 2
    )                                   AS pct_of_total
FROM fact_transactions
GROUP BY transaction_type
ORDER BY total_amount_crore DESC;


-- ----------------------------------------------------------------------------
-- Q11: Funds Outperforming Their Benchmark (Alpha > 0)
-- Business use: Identify actively managed funds generating positive alpha.
-- ----------------------------------------------------------------------------
SELECT
    fp.scheme_name,
    fp.fund_house,
    fp.category,
    ROUND(fp.return_3yr_pct, 2)     AS return_3yr_pct,
    ROUND(fp.benchmark_3yr_pct, 2)  AS benchmark_3yr_pct,
    ROUND(fp.alpha, 3)              AS alpha,
    ROUND(fp.beta, 3)               AS beta,
    ROUND(fp.sharpe_ratio, 3)       AS sharpe_ratio
FROM fact_performance fp
WHERE fp.alpha > 0
ORDER BY fp.alpha DESC;


-- ----------------------------------------------------------------------------
-- Q12: Sector Concentration in Equity Fund Portfolios
-- Business use: Understand sector diversification / concentration across funds.
-- ----------------------------------------------------------------------------
SELECT
    sector,
    COUNT(DISTINCT amfi_code)       AS num_funds,
    ROUND(AVG(weight_pct), 2)       AS avg_weight_pct,
    ROUND(SUM(market_value_cr), 2)  AS total_market_value_cr
FROM fact_portfolio
WHERE sector IS NOT NULL
GROUP BY sector
ORDER BY total_market_value_cr DESC;


-- ----------------------------------------------------------------------------
-- Q13: Investor Age Group vs Average SIP Amount
-- Business use: Demographic segmentation for product targeting.
-- ----------------------------------------------------------------------------
SELECT
    age_group,
    COUNT(*)                            AS sip_count,
    ROUND(AVG(amount_inr), 2)          AS avg_sip_amount_inr,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_amount_crore,
    COUNT(DISTINCT investor_id)         AS unique_investors
FROM fact_transactions
WHERE transaction_type = 'SIP'
  AND age_group IS NOT NULL
GROUP BY age_group
ORDER BY avg_sip_amount_inr DESC;


-- ----------------------------------------------------------------------------
-- Q14: T30 vs B30 City Investment Split
-- Business use: Assess geographic penetration (top cities vs rest of India).
-- ----------------------------------------------------------------------------
SELECT
    city_tier,
    COUNT(*)                            AS transactions,
    COUNT(DISTINCT investor_id)         AS unique_investors,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_amount_crore,
    ROUND(
        100.0 * SUM(amount_inr) /
        SUM(SUM(amount_inr)) OVER (), 2
    )                                   AS pct_of_total
FROM fact_transactions
WHERE city_tier IS NOT NULL
GROUP BY city_tier;


-- ----------------------------------------------------------------------------
-- Q15: Best Risk-Adjusted Funds (Sharpe Ratio > 1.0)
-- Business use: Identify funds delivering strong returns per unit of risk.
-- ----------------------------------------------------------------------------
SELECT
    fp.scheme_name,
    fp.fund_house,
    fp.category,
    ROUND(fp.sharpe_ratio, 3)       AS sharpe_ratio,
    ROUND(fp.sortino_ratio, 3)      AS sortino_ratio,
    ROUND(fp.return_3yr_pct, 2)     AS return_3yr_pct,
    ROUND(fp.std_dev_ann_pct, 2)    AS std_dev_ann_pct,
    fp.morningstar_rating
FROM fact_performance fp
WHERE fp.sharpe_ratio > 1.0
ORDER BY fp.sharpe_ratio DESC;
