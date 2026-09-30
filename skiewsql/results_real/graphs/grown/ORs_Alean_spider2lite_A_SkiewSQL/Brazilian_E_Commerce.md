# Skill graph — `Brazilian_E_Commerce` (2 skills)

**Skill `orders_normalized`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `order_date`, `order_status` |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `monthly_delivered_pivot` |
| validated_on | — |
| counter_examples | 0 |

_Normalized orders with order_id, order_date, and order_status._

```sql
SELECT
    "order_id",
    date("order_purchase_timestamp") AS "order_date",
    "order_status"
FROM "olist_orders"
```

---

**Skill `monthly_delivered_pivot`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `month` |
| output columns | `month`, `delivered_order_count_2016`, `delivered_order_count_2017`, `delivered_order_count_2018` |
| source tables | `orders_normalized` |
| depends_on (builds on) | `orders_normalized` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Pivoted monthly counts of delivered orders for years 2016, 2017, 2018._

```sql
SELECT
    CAST(strftime('%m', order_date) AS INTEGER) AS month,
    SUM(CASE WHEN CAST(strftime('%Y', order_date) AS INTEGER) = 2016 THEN 1 ELSE 0 END) AS delivered_order_count_2016,
    SUM(CASE WHEN CAST(strftime('%Y', order_date) AS INTEGER) = 2017 THEN 1 ELSE 0 END) AS delivered_order_count_2017,
    SUM(CASE WHEN CAST(strftime('%Y', order_date) AS INTEGER) = 2018 THEN 1 ELSE 0 END) AS delivered_order_count_2018
FROM orders_normalized
WHERE order_status = 'delivered'
GROUP BY month
```

---
