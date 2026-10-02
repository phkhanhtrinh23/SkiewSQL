# Skill graph — `Brazilian_E_Commerce` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute a report that shows, for each calendar month, the number of orders with status 'delivered' in each of the years 2016, 2017, and 2018, with one row per month and one column per year. Requ_

```sql
SELECT
  CAST(strftime('%m', order_delivered_customer_date) AS INTEGER) AS month,
  SUM(CASE WHEN CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) = 2016 THEN 1 ELSE 0 END) AS "2016",
  SUM(CASE WHEN CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) = 2017 THEN 1 ELSE 0 END) AS "2017",
  SUM(CASE WHEN CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) = 2018 THEN 1 ELSE 0 END) AS "2018"
FROM olist_orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND CAST(strftime('%Y', order_delivered_customer_date) AS INTEGER) IN (2016,2017,2018)
GROUP BY CAST(strftime('%m', order_delivered_customer_date) AS INTEGER)
ORDER BY month
```

---
