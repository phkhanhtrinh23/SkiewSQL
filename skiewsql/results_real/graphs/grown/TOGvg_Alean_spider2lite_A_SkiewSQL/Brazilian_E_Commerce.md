# Skill graph — `Brazilian_E_Commerce` (2 skills)

**Skill `delivered_orders_by_month_year`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `month`, `year` |
| output columns | `month`, `year`, `order_count` |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_delivered_orders_pivot` |
| validated_on | — |
| counter_examples | 0 |

_aggregated count of orders grouped by month and year, filtered by delivery status_

```sql
SELECT 
    strftime('%m', order_delivered_customer_date) AS month,
    strftime('%Y', order_delivered_customer_date) AS year,
    COUNT(order_id) AS order_count
FROM olist_orders
GROUP BY strftime('%m', order_delivered_customer_date), strftime('%Y', order_delivered_customer_date)
```

---

**Skill `monthly_delivered_orders_pivot`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `month` |
| output columns | `month`, `delivered_orders_2016`, `delivered_orders_2017`, `delivered_orders_2018` |
| source tables | `delivered_orders_by_month_year` |
| depends_on (builds on) | `delivered_orders_by_month_year` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_pivoted relation transforming year-based counts into separate columns per year, keyed by month_

```sql
SELECT month, COALESCE(SUM(CASE WHEN year = '2016' THEN order_count END), 0) AS delivered_orders_2016, COALESCE(SUM(CASE WHEN year = '2017' THEN order_count END), 0) AS delivered_orders_2017, COALESCE(SUM(CASE WHEN year = '2018' THEN order_count END), 0) AS delivered_orders_2018 FROM delivered_orders_by_month_year GROUP BY month
```

---
