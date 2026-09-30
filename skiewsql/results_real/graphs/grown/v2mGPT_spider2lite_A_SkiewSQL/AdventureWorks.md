# Skill graph — `AdventureWorks` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `salesperson`, `salesorderheader`, `SalesPersonQuotaHistory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each salesperson and for each year, compute the difference between that salesperson's annual total sales and that salesperson's annual sales quota, and present one row per salesperson per ye_

```sql
SELECT
  s.businessentityid AS salesperson_businessentityid,
  -- year for sales and quotas; extract year from date/timestamp columns present in this chunk
  CAST(strftime('%Y', soh.orderdate) AS INTEGER) AS sale_year,
  SUM(soh.totaldue) AS annual_total_sales,
  spqh.SalesQuota AS annual_sales_quota,
  SUM(soh.totaldue) - spqh.SalesQuota AS difference
FROM salesperson s
LEFT JOIN salesorderheader soh
  ON s.businessentityid = soh.salespersonid
LEFT JOIN SalesPersonQuotaHistory spqh
  ON s.businessentityid = spqh.BusinessEntityID
  AND CAST(strftime('%Y', spqh.QuotaDate) AS INTEGER) = CAST(strftime('%Y', soh.orderdate) AS INTEGER)
GROUP BY
  s.businessentityid,
  sale_year,
  spqh.SalesQuota
```

---
