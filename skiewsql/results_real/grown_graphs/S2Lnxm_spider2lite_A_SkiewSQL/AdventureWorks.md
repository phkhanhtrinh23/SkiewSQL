# Skill graph — `AdventureWorks` (4 skills)

**Skill `sales_transactions_with_year`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `sale_transaction_id` |
| output columns | `salesperson_id`, `sale_date`, `sale_year`, `sale_amount` |
| source tables | `salesorderheader` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `annual_sales_per_salesperson` |
| validated_on | — |
| counter_examples | 0 |

_All individual sales transactions normalized with a calendar year extracted from the sale date and canonical salesperson identifier. Keep monetary amount as a numeric value suitable for aggregation._

```sql
SELECT
  h.salesorderid AS sale_transaction_id,
  h.salespersonid AS salesperson_id,
  h.orderdate AS sale_date,
  CAST(strftime('%Y', h.orderdate) AS INTEGER) AS sale_year,
  h.totaldue AS sale_amount
FROM salesorderheader h
```

---

**Skill `annual_sales_per_salesperson`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `salesperson_id`, `sale_year` |
| output columns | `salesperson_id`, `year`, `annual_total_sales` |
| source tables | `sales_transactions_with_year` |
| depends_on (builds on) | `sales_transactions_with_year` |
| depended-on by (builds on this) | `sales_vs_quota_by_year` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate total sales amount per salesperson per calendar year by summing sale_amount across transactions in that year._

```sql
SELECT
  stwy.salesperson_id AS salesperson_id,
  stwy.sale_year AS year,
  SUM(stwy.sale_amount) AS annual_total_sales
FROM
  sales_transactions_with_year stwy
GROUP BY
  stwy.salesperson_id,
  stwy.sale_year
```

---

**Skill `annual_quotas_per_salesperson`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `salesperson_id`, `year` |
| output columns | `salesperson_id`, `year`, `annual_quota`, `quota_date`, `rowguid`, `modified_date` |
| source tables | `SalesPersonQuotaHistory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `sales_vs_quota_by_year` |
| validated_on | — |
| counter_examples | 0 |

_Quota records normalized to one row per salesperson per year, with the quota amount and a year value (either from an explicit quota year field or derived as provided by schema). Include all quota records even if no sales exist that year._

```sql
SELECT
  SalesPersonQuotaHistory.BusinessEntityID AS salesperson_id,
  CAST(strftime('%Y', SalesPersonQuotaHistory.QuotaDate) AS INTEGER) AS year,
  SalesPersonQuotaHistory.SalesQuota AS annual_quota,
  SalesPersonQuotaHistory.QuotaDate AS quota_date,
  SalesPersonQuotaHistory.rowguid AS rowguid,
  SalesPersonQuotaHistory.ModifiedDate AS modified_date
FROM SalesPersonQuotaHistory
```

---

**Skill `sales_vs_quota_by_year`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `salesperson_id`, `year` |
| output columns | `salesperson_id`, `year`, `annual_total_sales`, `annual_quota`, `difference` |
| source tables | `annual_sales_per_salesperson`, `annual_quotas_per_salesperson` |
| depends_on (builds on) | `annual_sales_per_salesperson`, `annual_quotas_per_salesperson` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Full outer join (or union-style combine) of annual_sales_per_salesperson and annual_quotas_per_salesperson to produce one row per salesperson per year present in either source, with NULLs filled as zero or left null as appropriate; compute the difference as annual_total_sales - annual_quota._

```sql
SELECT
  COALESCE(s.salesperson_id, q.salesperson_id) AS salesperson_id,
  COALESCE(s.year, q.year) AS year,
  COALESCE(s.annual_total_sales, 0.0) AS annual_total_sales,
  q.annual_quota AS annual_quota,
  COALESCE(s.annual_total_sales, 0.0) - q.annual_quota AS difference
FROM annual_sales_per_salesperson s
FULL OUTER JOIN annual_quotas_per_salesperson q
  ON s.salesperson_id = q.salesperson_id AND s.year = q.year
```

---
