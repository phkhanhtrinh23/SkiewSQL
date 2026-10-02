# Skill graph — `oracle_sql` (5 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `packaging_relations` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average of the total quantity for each final packaging combination, where for each combination you fully expand any nested packaging relationships and sum only the quantities of the _

```sql
SELECT
  pr.packaging_id AS packaging_id,
  pr.contains_id AS contains_id,
  pr.qty AS qty
FROM packaging_relations pr
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `orders`, `orderlines`, `inventory`, `locations`, `purchases` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | Which products were picked for order 421, and what is the average number of units picked for each product, using FIFO (First-In, First-Out) method? |
| counter_examples | 1 |

_Task: For order 423, compute for each order line the exact pick plan listing which product IDs, aisle identifiers, and positions (locations) to pick from and the pick quantities from each location so _

```sql
SELECT
  o.id AS order_id,
  ol.id AS order_line_id,
  ol.product_id,
  ol.qty AS order_line_qty,
  ol.id AS order_line_seq,           -- preserve sequence/orderline identifier for ordering later
  i.id AS inventory_id,
  i.location_id,
  l.aisle AS location_aisle,
  l.position AS location_position,
  l.warehouse AS warehouse_id,
  i.qty AS inventory_qty,
  p.purchased AS purchase_date,
  ol.qty AS needed_for_line
FROM orders o
JOIN orderlines ol ON ol.order_id = o.id
LEFT JOIN inventory i ON i.product_id = ol.product_id
LEFT JOIN locations l ON l.id = i.location_id
LEFT JOIN purchases p ON p.id = i.purchase_id
WHERE o.id = 423
  AND l.warehouse = 1
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `monthly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify all products whose monthly Sales-to-CMA Ratio (actual sales divided by the centered 12-month moving average computed using the specified 12-month overlapping windows) remained strictly _

```sql
SELECT
  ms.product_id,
  ms.mth,
  ms.qty AS sales_qty
FROM monthly_sales ms
WHERE ms.mth BETWEEN '2016-01-01' AND '2017-12-01'
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `monthly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average forecasted annual sales for products 4160 and 7790 for the year 2018, where forecasts are produced from monthly sales data (January 2016 onward) using the first 36 months of _

```sql
SELECT
  ms.product_id,
  ms.mth,
  ms.qty
FROM
  monthly_sales ms
WHERE
  ms.mth >= '2016-01-01'
  AND ms.mth < date('2016-01-01', '+36 months')
  AND ms.product_id IN (4160, 7790)
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `products`, `inventory`, `product_minimums` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Starting from December 2018 ending inventory levels and applying a recursive monthly inventory adjustment for each product throughout 2019 where each month's ending inventory is computed from th_

```sql
SELECT
  p.id AS product_id,
  -- December 2018 ending inventory for each product is taken from inventory.qty where purchase_id / location unspecified in this chunk.
  -- Keep inventory.id/location_id/purchase_id to allow joins later; qty is the starting (Dec 2018) ending inventory value to be used for recursive months.
  inventory.qty AS dec_2018_ending_qty,
  inventory.id AS inventory_id,
  inventory.location_id,
  inventory.purchase_id,
  pm.qty_minimum AS qty_minimum,
  pm.qty_purchase AS qty_purchase
FROM products p
LEFT JOIN inventory ON inventory.product_id = p.id
LEFT JOIN product_minimums pm ON pm.product_id = p.id
```

---
