# Skill graph — `AdventureWorks` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `salesperson`, `salesorderheader`, `salesorderdetail`, `SalesPersonQuotaHistory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each salesperson and for each year, compute the difference between that salesperson's annual total sales and their annual sales quota; return one row per salesperson per year containing the _

```sql
SELECT
  s.businessentityid AS salesperson_id,
  CAST(strftime('%Y', so.orderdate) AS INTEGER) AS year,
  so.salesorderid,
  sd.salesorderdetailid,
  sd.orderqty,
  sd.unitprice,
  so.totaldue,
  q.QuotaDate,
  q.SalesQuota
FROM salesperson s
LEFT JOIN salesorderheader so
  ON s.businessentityid = so.salespersonid
LEFT JOIN salesorderdetail sd
  ON so.salesorderid = sd.salesorderid
LEFT JOIN SalesPersonQuotaHistory q
  ON s.businessentityid = q.BusinessEntityID
```

---
