# Skill graph — `delivery_center` (3 skills)

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

_Task: Find the store (from the dataset created by joining orders with store information) that has the largest total count of orders, and for that store compute the count of that store's orders that ap_

```sql
SELECT
  s.store_id,
  s.store_name,
  o.order_id,
  o.payment_order_id,
  d.delivery_id,
  d.delivery_order_id,
  d.delivery_status
FROM orders o
JOIN stores s ON o.store_id = s.store_id
LEFT JOIN deliveries d ON o.order_id = d.delivery_order_id
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `hubs`, `stores`, `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: List the hub identifiers and their finished order counts in February and March, for hubs whose finished orders increased by more than 20% from February to March.
Required outputs: hub identifier_

```sql
SELECT
  hubs.hub_id,
  hubs.hub_name,
  orders.order_created_month,
  COUNT(orders.order_id) AS finished_orders_count
FROM hubs
JOIN stores ON stores.hub_id = hubs.hub_id
JOIN orders ON orders.store_id = stores.store_id
WHERE orders.order_status = 'FINISHED'
  AND orders.order_created_year IS NOT NULL
  AND orders.order_created_month IN (2, 3)
GROUP BY
  hubs.hub_id,
  hubs.hub_name,
  orders.order_created_month
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `drivers`, `deliveries`, `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the five delivery drivers who have the highest average number of daily deliveries and return each driver's identifier along with their average daily deliveries.
Required outputs: driver ide_

```sql
SELECT
  d.driver_id,
  del.delivery_id,
  del.delivery_order_id,
  del.delivery_status,
  del.delivery_distance_meters,
  o.order_moment_delivered,
  -- derive delivery_date from available timestamp in this chunk
  DATE(o.order_moment_delivered) AS delivery_date
FROM drivers d
JOIN deliveries del
  ON d.driver_id = del.driver_id
LEFT JOIN orders o
  ON del.delivery_order_id = o.delivery_order_id
```

---
