# Database Loading Report — Day 2

**Generated:** 2026-06-24 09:55:08  
**Database:** bluestock_mf.db  
**Project:** Bluestock Fintech — Mutual Fund Analytics  

---

## Tables Loaded

| Table | Rows Loaded |
|-------|------------|
| dim_fund | 40 |
| dim_date | 1,608 |
| fact_nav | 46,000 |
| fact_transactions | 32,778 |
| fact_performance | 40 |
| fact_aum | 90 |
| fact_portfolio | 322 |
| fact_sip_inflows | 48 |
| fact_category_inflows | 144 |
| fact_folio_count | 21 |
| fact_benchmark | 8,050 |

## Row Count Verification

```
  ✓  dim_fund: source=40 | db=40
  ✓  dim_date: source=1,608 | db=1,608
  ✓  fact_nav: source=46,000 | db=46,000
  ✓  fact_transactions: source=32,778 | db=32,778
  ✓  fact_performance: source=40 | db=40
  ✓  fact_aum: source=90 | db=90
  ✓  fact_portfolio: source=322 | db=322
  ✓  fact_sip_inflows: source=48 | db=48
  ✓  fact_category_inflows: source=144 | db=144
  ✓  fact_folio_count: source=21 | db=21
  ✓  fact_benchmark: source=8,050 | db=8,050
```

**Elapsed time:** 1.23s
