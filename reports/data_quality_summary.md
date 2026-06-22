# Data Quality Summary Report

**Generated:** 2026-06-22 19:26:29  
**Pipeline:** data_ingestion.py v1.0.0  
**Project:** Bluestock Fintech — Mutual Fund Analytics  

---

## Dataset: `all_funds_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 19,882 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 3,105 | 15.62% | 116468.5 | 123464.5 |
| nav | 2,774 | 13.95% | -125.0891 | 310.5078 |

---

## Dataset: `axis_bluechip_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 3,579 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 0 | 0.00% | 119092.0 | 119092.0 |
| nav | 805 | 22.49% | 589.2446 | 7262.0665 |

---

## Dataset: `fund_master`

| Metric | Value |
|--------|-------|
| Total Rows | 31 |
| Total Columns | 10 |
| Duplicate Rows | 0 |
| Numeric Columns | 3 |
| Object Columns | 7 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 3 | 9.68% | 117997.75 | 122139.75 |
| aum_cr | 0 | 0.00% | -32693.9125 | 98977.9875 |
| expense_ratio | 0 | 0.00% | -0.2425 | 1.3775 |

---

## Dataset: `hdfc_top100_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 3,105 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 0 | 0.00% | 125497.0 | 125497.0 |
| nav | 0 | 0.00% | -95.5283 | 266.6733 |

---

## Dataset: `icici_bluechip_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 3,321 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 0 | 0.00% | 120503.0 | 120503.0 |
| nav | 0 | 0.00% | -36.9094 | 147.6557 |

---

## Dataset: `kotak_bluechip_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 3,315 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 0 | 0.00% | 120841.0 | 120841.0 |
| nav | 0 | 0.00% | -103.1184 | 294.5096 |

---

## Dataset: `nippon_largecap_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 3,312 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 0 | 0.00% | 118632.0 | 118632.0 |
| nav | 0 | 0.00% | -27.8945 | 113.1308 |

---

## Dataset: `sbi_bluechip_nav`

| Metric | Value |
|--------|-------|
| Total Rows | 3,250 |
| Total Columns | 7 |
| Duplicate Rows | 0 |
| Numeric Columns | 2 |
| Object Columns | 5 |
| Datetime Columns | 0 |

### Missing Values

No missing values detected. Dataset is complete.

### Data Type Issues

No data type issues detected.

### Outlier Detection (IQR Method)

| Column | Outlier Count | Outlier % | Lower Fence | Upper Fence |
|--------|--------------|-----------|-------------|-------------|
| scheme_code | 0 | 0.00% | 119551.0 | 119551.0 |
| nav | 0 | 0.00% | 52.3678 | 200.6905 |

---

## AMFI Scheme Code Validation

| Check | Result |
|-------|--------|
| Scheme codes in fund_master | 28 |
| Scheme codes in nav_history | 6 |
| Missing from nav_history | 22 |
| Duplicate codes in fund_master | 3 |

### Scheme Codes Missing from NAV History

| Scheme Code |
|-------------|
| 100119 |
| 118825 |
| 119028 |
| 119189 |
| 119233 |
| 119597 |
| 119598 |
| 119683 |
| 119780 |
| 119822 |
| 119823 |
| 120178 |
| 120465 |
| 120505 |
| 120573 |
| 120586 |
| 120587 |
| 120684 |
| 120716 |
| 120819 |
| 120828 |
| 125354 |

### Duplicate Scheme Codes in Fund Master

| Scheme Code | Count |
|-------------|-------|
| 120503 | 2 |
| 119598 | 2 |
| 119551 | 2 |

## Overall Summary

| Metric | Value |
|--------|-------|
| Datasets Profiled | 8 |
| Total Records | 39,795 |
| Total Missing Values | 0 |
| Total Duplicate Rows | 0 |
