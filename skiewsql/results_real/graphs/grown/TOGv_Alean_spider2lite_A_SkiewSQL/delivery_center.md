# Skill graph — `delivery_center` (2 skills)

**Skill `store_order_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `store_id` |
| output columns | `store_id`, `total_orders`, `delivered_orders` |
| source tables | `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `top_store_ratio` |
| validated_on | — |
| counter_examples | 0 |

_aggregates order records per store, yielding total order count and delivered order count_

```sql
SELECT
    store_id,
    COUNT(order_id) AS total_orders,
    SUM(CASE WHEN order_status = 'DELIVERED' THEN 1 ELSE 0 END) AS delivered_orders
FROM orders
GROUP BY store_id
```

---

**Skill `top_store_ratio`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `store_id` |
| output columns | `store_id`, `delivered_to_total_ratio` |
| source tables | `store_order_counts` |
| depends_on (builds on) | `store_order_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_ranks stores by total order count, computes the delivered-to-total ratio, and filters to the highest-ranked store_

```sql
SELECT s.store_id, s.delivered_orders * 1.0 / s.total_orders AS delivered_to_total_ratio
FROM store_order_counts s
```

---
