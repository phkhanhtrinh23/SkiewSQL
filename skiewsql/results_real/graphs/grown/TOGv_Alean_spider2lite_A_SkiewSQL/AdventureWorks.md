# Skill graph — `AdventureWorks` (2 skills)

**Skill `salesperson_annual_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `salespersonid`, `year` |
| output columns | `salesperson`, `year`, `total_sales` |
| source tables | `salesorderheader` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregates sales transactions to compute total revenue per salesperson per year_

```sql
SELECT soh.salespersonid AS salesperson, strftime('%Y', soh.orderdate) AS year, SUM(soh.subtotal) AS total_sales FROM salesorderheader soh GROUP BY soh.salespersonid, strftime('%Y', soh.orderdate)
```

---

**Skill `salesperson_annual_quotas`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `BusinessEntityID`, `year` |
| output columns | `salesperson`, `year`, `annual_quota` |
| source tables | `SalesPersonQuotaHistory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregates quota records to compute the assigned sales target per salesperson per year_

```sql
SELECT BusinessEntityID AS salesperson, strftime('%Y', QuotaDate) AS year, SUM(SalesQuota) AS annual_quota FROM SalesPersonQuotaHistory GROUP BY BusinessEntityID, strftime('%Y', QuotaDate)
```

---
