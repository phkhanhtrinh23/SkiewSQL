# Skill graph — `delivery_center` (2 skills)

**Skill `store_total_orders`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `store_id` |
| output columns | `store_id`, `total_orders` |
| source tables | `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_total number of orders per store_

```sql
SELECT store_id, COUNT(order_id) AS total_orders FROM orders GROUP BY store_id
```

---

**Skill `store_delivered_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `store_id` |
| output columns | `store_id`, `delivered_orders` |
| source tables | `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_number of orders per store with a delivered delivery status_

```sql
SELECT store_id, COUNT(*) AS delivered_orders
FROM orders
WHERE order_status = 'DELIVERED'
GROUP BY store_id
```

---
