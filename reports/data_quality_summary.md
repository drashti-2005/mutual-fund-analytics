# Data Quality Summary Report

**Generated:** 2026-06-23 18:13:32  
**Pipeline:** data_ingestion.py v1.0.0  
**Project:** Bluestock Fintech — Mutual Fund Analytics  

---

## Dataset: `01_fund_master`

| Metric | Value |
|--------|-------|
| Total Rows | 40 |
| Total Columns | 15 |
| Duplicate Rows | 0 |
| Numeric Columns | 5 |
| Object Columns | 10 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| amfi_code | 17 | 42.50% | 115318.5 | 124156.5 |
| expense_ratio_pct | 0 | 0.00% | -0.3412 | 2.6688 |
| exit_load_pct | 8 | 20.00% | 1.0 | 1.0 |
| min_sip_amount | 0 | 0.00% | 500.0 | 500.0 |
| min_lumpsum_amount | 4 | 10.00% | 1000.0 | 1000.0 |

---

## Dataset: `02_nav_history`

| Metric | Value |
|--------|-------|
| Total Rows | 46,000 |
| Total Columns | 3 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 1 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| amfi_code | 19,550 | 42.50% | 115318.5 | 124156.5 |
| nav | 3,494 | 7.60% | -217.582 | 547.091 |

---

## Dataset: `03_aum_by_fund_house`

| Metric | Value |
|--------|-------|
| Total Rows | 90 |
| Total Columns | 5 |
| Duplicate Rows | 0 |
| Numeric Columns | 3 |
| Object Columns | 2 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| aum_lakh_crore | 5 | 5.56% | -2.2 | 10.4 |
| aum_crore | 5 | 5.56% | -220000.0 | 1040000.0 |
| num_schemes | 0 | 0.00% | -55.0 | 345.0 |

---

## Dataset: `04_monthly_sip_inflows`

| Metric | Value |
|--------|-------|
| Total Rows | 48 |
| Total Columns | 6 |
| Duplicate Rows | 0 |
| Numeric Columns | 5 |
| Object Columns | 1 |
| Datetime Columns | 0 |

### Missing Values

| Column | Missing Count | Missing % | Completeness % |
|--------|--------------|-----------|----------------|
| yoy_growth_pct | 12 | 25.00% | 75.00% |

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| sip_inflow_crore | 0 | 0.00% | -4770.125 | 44372.875 |
| active_sip_accounts_crore | 0 | 0.00% | 2.825 | 11.585 |
| new_sip_accounts_lakh | 2 | 4.17% | 7.5938 | 10.7437 |
| sip_aum_lakh_crore | 0 | 0.00% | -1.3125 | 17.6275 |
| yoy_growth_pct | 0 | 0.00% | -10.5988 | 71.6512 |

---

## Dataset: `05_category_inflows`

| Metric | Value |
|--------|-------|
| Total Rows | 144 |
| Total Columns | 3 |
| Duplicate Rows | 0 |
| Numeric Columns | 1 |
| Object Columns | 2 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| net_inflow_crore | 12 | 8.33% | -3452.875 | 10558.125 |

---

## Dataset: `06_industry_folio_count`

| Metric | Value |
|--------|-------|
| Total Rows | 21 |
| Total Columns | 6 |
| Duplicate Rows | 0 |
| Numeric Columns | 5 |
| Object Columns | 1 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| total_folios_crore | 0 | 0.00% | 3.015 | 36.415 |
| equity_folios_crore | 0 | 0.00% | 2.12 | 25.48 |
| debt_folios_crore | 0 | 0.00% | 0.44 | 5.08 |
| hybrid_folios_crore | 0 | 0.00% | 0.18 | 2.18 |
| others_folios_crore | 0 | 0.00% | 0.29 | 3.65 |

---

## Dataset: `07_scheme_performance`

| Metric | Value |
|--------|-------|
| Total Rows | 40 |
| Total Columns | 19 |
| Duplicate Rows | 0 |
| Numeric Columns | 14 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| amfi_code | 17 | 42.50% | 115318.5 | 124156.5 |
| return_1yr_pct | 3 | 7.50% | 4.7487 | 23.3788 |
| return_3yr_pct | 7 | 17.50% | 6.2638 | 21.6538 |
| return_5yr_pct | 0 | 0.00% | 4.4725 | 25.4525 |
| benchmark_3yr_pct | 5 | 12.50% | 4.5625 | 20.9025 |
| alpha | 0 | 0.00% | -0.3313 | 2.9188 |
| beta | 6 | 15.00% | 0.725 | 1.165 |
| sharpe_ratio | 6 | 15.00% | 0.685 | 1.165 |
| sortino_ratio | 5 | 12.50% | 0.7188 | 2.1887 |
| std_dev_ann_pct | 6 | 15.00% | 6.5 | 26.5 |
| max_drawdown_pct | 0 | 0.00% | -41.2738 | 1.9563 |
| aum_crore | 0 | 0.00% | -13686.25 | 69211.75 |
| expense_ratio_pct | 0 | 0.00% | -0.3412 | 2.6688 |
| morningstar_rating | 0 | 0.00% | 2.5 | 6.5 |

---

## Dataset: `08_investor_transactions`

| Metric | Value |
|--------|-------|
| Total Rows | 32,778 |
| Total Columns | 13 |
| Duplicate Rows | 0 |
| Numeric Columns | 3 |
| Object Columns | 10 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| amfi_code | 14,047 | 42.85% | 115315.5 | 124159.5 |
| amount_inr | 977 | 2.98% | -276103.875 | 468581.125 |
| annual_income_lakh | 1,145 | 3.49% | -29.6 | 77.6 |

---

## Dataset: `09_portfolio_holdings`

| Metric | Value |
|--------|-------|
| Total Rows | 322 |
| Total Columns | 8 |
| Duplicate Rows | 0 |
| Numeric Columns | 4 |
| Object Columns | 4 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| amfi_code | 138 | 42.86% | 115318.375 | 124157.375 |
| weight_pct | 8 | 2.48% | -5.8387 | 25.7713 |
| market_value_cr | 0 | 0.00% | -931.9975 | 2923.2025 |
| current_price_inr | 0 | 0.00% | -3666.4988 | 11662.7912 |

---

## Dataset: `10_benchmark_indices`

| Metric | Value |
|--------|-------|
| Total Rows | 8,050 |
| Total Columns | 3 |
| Duplicate Rows | 0 |
| Numeric Columns | 1 |
| Object Columns | 2 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| close_value | 197 | 2.45% | -32760.99 | 62119.15 |

---

## AMFI Scheme Code Validation

> `scheme_code` column not found in one or both datasets — skipping scheme validation.

## Overall Summary

| Metric | Value |
|--------|-------|
| Datasets Profiled | 10 |
| Total Records | 87,533 |
| Total Missing Values | 12 |
| Total Duplicate Rows | 0 |
