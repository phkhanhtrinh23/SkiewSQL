# Skill graph — `delivery_center` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `orders`, `stores`, `deliveries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find which store (from the dataset of orders joined with store information) has the highest total number of orders, and for that store compute the ratio of that store's orders which appear in th_

```sql
SELECT
    stores.store_id,
    stores.store_name,
    COUNT(orders.order_id) AS total_orders_for_store,
    SUM(CASE WHEN deliveries.delivery_id IS NOT NULL AND deliveries.delivery_status = 'DELIVERED' THEN 1 ELSE 0 END) AS delivered_orders_for_store,
    CAST(SUM(CASE WHEN deliveries.delivery_id IS NOT NULL AND deliveries.delivery_status = 'DELIVERED' THEN 1 ELSE 0 END) AS DECIMAL) 
      / NULLIF(COUNT(orders.order_id), 0) AS delivered_ratio
FROM orders
JOIN stores ON orders.store_id = stores.store_id
LEFT JOIN deliveries ON orders.delivery_order_id = deliveries.delivery_order_id
GROUP BY stores.store_id, stores.store_name
```

---
