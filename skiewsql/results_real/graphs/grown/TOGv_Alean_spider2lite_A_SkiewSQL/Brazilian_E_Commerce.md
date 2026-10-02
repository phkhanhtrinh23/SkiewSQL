# Skill graph — `Brazilian_E_Commerce` (2 skills)

**Skill `delivered_orders_agg`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `month`, `year` |
| output columns | `month`, `year`, `delivered_order_count` |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_year_pivot` |
| validated_on | — |
| counter_examples | 0 |

_counts of delivered orders grouped by month and year_

```sql
SELECT
    strftime('%m', order_delivered_customer_date) AS month,
    strftime('%Y', order_delivered_customer_date) AS year,
    COUNT(order_id) AS delivered_order_count
FROM olist_orders
WHERE order_status = 'delivered'
GROUP BY month, year
```

---

**Skill `monthly_year_pivot`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `month` |
| output columns | `month`, `delivered_orders_2016`, `delivered_orders_2017`, `delivered_orders_2018` |
| source tables | `delivered_orders_agg` |
| depends_on (builds on) | `delivered_orders_agg` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_pivots the aggregated counts so each row corresponds to a month and columns correspond to the count for each year_

```sql
SELECT
    month,
    SUM(CASE WHEN year = '2016' THEN delivered_order_count ELSE 0 END) AS delivered_orders_2016,
    SUM(CASE WHEN year = '2017' THEN delivered_order_count ELSE 0 END) AS delivered_orders_2017,
    SUM(CASE WHEN year = '2018' THEN delivered_order_count ELSE 0 END) AS delivered_orders_2018
FROM delivered_orders_agg
GROUP BY month
```

---
