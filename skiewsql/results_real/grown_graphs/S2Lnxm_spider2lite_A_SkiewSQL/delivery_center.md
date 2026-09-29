# Skill graph — `delivery_center` (12 skills)

**Skill `orders_with_store_join`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `store_id`, `store_identifiers...` |
| source tables | `orders`, `stores` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `store_order_flags` |
| validated_on | — |
| counter_examples | 0 |

_All orders joined to their store information so each row represents an order together with the identifying store columns (do not aggregate here)._

```sql
SELECT
  orders.order_id,
  stores.store_id,
  stores.store_name AS "store_identifiers..."
FROM orders
LEFT JOIN stores ON orders.store_id = stores.store_id
```

---

**Skill `deliveries_delivered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `delivery_id` |
| output columns | `order_id`, `delivery_id`, `status` |
| source tables | `deliveries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `store_order_flags` |
| validated_on | — |
| counter_examples | 0 |

_Subset of deliveries rows that indicate a delivered order (deliveries with status = 'DELIVERED'); one row per delivery event._

```sql
SELECT
  delivery_order_id AS order_id,
  delivery_id AS delivery_id,
  delivery_status AS status
FROM
  deliveries
WHERE
  delivery_status = 'DELIVERED'
```

---

**Skill `store_order_flags`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `store_id`, `is_delivered_flag` |
| source tables | `orders`, `deliveries` |
| depends_on (builds on) | `orders_with_store_join`, `deliveries_delivered` |
| depended-on by (builds on this) | `store_order_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_Left-join orders_with_store_join to deliveries_delivered to mark, for each order, whether that order has at least one matching delivered delivery row (boolean/flag). One row per order._

```sql
SELECT
  o.order_id,
  o.store_id,
  CASE WHEN d.order_id IS NOT NULL THEN 1 ELSE 0 END AS is_delivered_flag
FROM orders_with_store_join o
LEFT JOIN deliveries_delivered d
  ON o.order_id = d.order_id
```

---

**Skill `store_order_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `store_id` |
| output columns | `store_id`, `total_orders_for_store`, `delivered_orders_for_store`, `delivered_ratio` |
| source tables | `store_order_flags` |
| depends_on (builds on) | `store_order_flags` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate counts per store: total number of orders (from orders_with_store_join) and number of orders that have a delivered delivery (sum of is_delivered_flag). One row per store._

```sql
SELECT
  sof.store_id AS store_id,
  COUNT(sof.order_id) AS total_orders_for_store,
  SUM(CASE WHEN sof.is_delivered_flag THEN 1 ELSE 0 END) AS delivered_orders_for_store,
  CASE WHEN COUNT(sof.order_id) = 0 THEN 0.0 ELSE SUM(CASE WHEN sof.is_delivered_flag THEN 1.0 ELSE 0.0 END) / COUNT(sof.order_id) END AS delivered_ratio
FROM store_order_flags AS sof
GROUP BY sof.store_id
```

---

**Skill `finished_orders_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `hub_id`, `completed_date` |
| source tables | `orders`, `stores` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `orders_with_month_year` |
| validated_on | — |
| counter_examples | 0 |

_Select finished order events/rows with their order id, hub id, and the order completion date; restrict to orders whose status qualifies as 'finished' (business-defined) and that have a non-null completion date._

```sql
SELECT
  o.order_id,
  s.hub_id,
  o.order_moment_finished AS completed_date
FROM orders o
JOIN stores s ON o.store_id = s.store_id
WHERE o.order_status IN ('DELIVERED', 'FINISHED', 'COMPLETED')
  AND o.order_moment_finished IS NOT NULL
```

---

**Skill `orders_with_month_year`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `hub_id`, `completed_date`, `year`, `month` |
| source tables | `orders`, `stores`, `finished_orders_events` |
| depends_on (builds on) | `finished_orders_events` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize each finished order to include explicit year and month extracted from the completion date, and ensure the hub identifier is canonicalized (e.g., hub id or hub name)._

```sql
SELECT
  o.order_id AS order_id,
  COALESCE(foe.hub_id, s.hub_id) AS hub_id,
  COALESCE(foe.completed_date, o.order_moment_finished) AS completed_date,
  CAST(strftime('%Y', COALESCE(foe.completed_date, o.order_moment_finished)) AS INTEGER) AS year,
  CAST(strftime('%m', COALESCE(foe.completed_date, o.order_moment_finished)) AS INTEGER) AS month
FROM orders o
LEFT JOIN stores s ON o.store_id = s.store_id
LEFT JOIN finished_orders_events foe ON o.order_id = foe.order_id
WHERE COALESCE(foe.completed_date, o.order_moment_finished) IS NOT NULL
```

---

**Skill `monthly_finished_counts_per_hub`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `hub_id`, `order_created_year`, `order_created_month` |
| output columns | `hub_id`, `year`, `month`, `finished_count` |
| source tables | `orders`, `stores` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `feb_mar_comparison_per_hub` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate normalized finished orders to count finished orders per hub for each year and month (one row per hub-year-month)._

```sql
SELECT
  s.hub_id AS hub_id,
  o.order_created_year AS year,
  o.order_created_month AS month,
  COUNT(o.order_id) AS finished_count
FROM orders o
JOIN stores s ON o.store_id = s.store_id
WHERE o.order_status = 'FINISHED'
  AND o.order_moment_finished IS NOT NULL
GROUP BY s.hub_id, o.order_created_year, o.order_created_month
```

---

**Skill `feb_mar_comparison_per_hub`** — category `RESHAPE`

| field | value |
|---|---|
| grain (one row per) | `hub_id`, `year` |
| output columns | `hub_id`, `year`, `feb_finished_count`, `mar_finished_count`, `pct_change` |
| source tables | `monthly_finished_counts_per_hub` |
| depends_on (builds on) | `monthly_finished_counts_per_hub` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Reshape or join the monthly counts to produce one row per hub and year with separate columns for February and March finished counts, filter to rows where both months exist and February count > 0, and compute the percent change (march - feb) / feb._

```sql
SELECT
  mfh.hub_id,
  mfh.year,
  SUM(CASE WHEN mfh.month = 2 THEN mfh.finished_count ELSE 0 END) AS feb_finished_count,
  SUM(CASE WHEN mfh.month = 3 THEN mfh.finished_count ELSE 0 END) AS mar_finished_count,
  CASE
    WHEN SUM(CASE WHEN mfh.month = 2 THEN mfh.finished_count ELSE 0 END) = 0 THEN NULL
    ELSE (CAST(SUM(CASE WHEN mfh.month = 3 THEN mfh.finished_count ELSE 0 END) AS REAL) - SUM(CASE WHEN mfh.month = 2 THEN mfh.finished_count ELSE 0 END)) / CAST(SUM(CASE WHEN mfh.month = 2 THEN mfh.finished_count ELSE 0 END) AS REAL)
  END AS pct_change
FROM monthly_finished_counts_per_hub AS mfh
GROUP BY mfh.hub_id, mfh.year
HAVING
  SUM(CASE WHEN mfh.month = 2 THEN mfh.finished_count ELSE 0 END) > 0
  AND SUM(CASE WHEN mfh.month = 2 THEN 1 ELSE 0 END) > 0
  AND SUM(CASE WHEN mfh.month = 3 THEN 1 ELSE 0 END) > 0
```

---

**Skill `driver_deliveries_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `delivery_id` |
| output columns | `driver_id`, `delivery_date`, `delivery_id` |
| source tables | `deliveries`, `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `driver_average_daily_deliveries` |
| validated_on | — |
| counter_examples | 0 |

_All delivery event records (one row per delivery) with the driver identifier and the delivery date extracted; include only events that can be attributed to a driver._

```sql
SELECT
  d.driver_id AS driver_id,
  DATE(o.order_moment_delivered) AS delivery_date,
  d.delivery_id AS delivery_id
FROM deliveries d
JOIN orders o
  ON d.delivery_order_id = o.delivery_order_id
WHERE d.driver_id IS NOT NULL
  AND o.order_moment_delivered IS NOT NULL
```

---

**Skill `driver_daily_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `driver_id`, `DATE(delivery_status /* placeholder */)` |
| output columns | `driver_id`, `delivery_date`, `deliveries_that_day` |
| source tables | `deliveries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `driver_average_daily_deliveries` |
| validated_on | — |
| counter_examples | 0 |

_Count of deliveries per driver per distinct day (one row per driver per day) — i.e., number of deliveries a driver made on each calendar day they worked._

```sql
SELECT
  driver_id,
  DATE(delivery_status /* placeholder to allow DATE cast if status contains datetime; will be replaced by actual datetime column in real data */) AS delivery_date,
  COUNT(delivery_id) AS deliveries_that_day,
  MIN(delivery_id) AS delivery_id -- carry a source id to keep joinability (one example id per group)
FROM deliveries
WHERE delivery_id IS NOT NULL
GROUP BY driver_id, DATE(delivery_status /* placeholder */)
```

---

**Skill `driver_totals_and_days`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `driver_id` |
| output columns | `driver_id`, `total_deliveries`, `distinct_delivery_days` |
| source tables | `deliveries` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `driver_average_daily_deliveries` |
| validated_on | — |
| counter_examples | 0 |

_For each driver, compute the total number of deliveries and the number of distinct delivery days (keep one row per driver)._

```sql
SELECT
  d.driver_id AS driver_id,
  COUNT(d.delivery_id) AS total_deliveries,
  COUNT(DISTINCT date(d.delivery_id, 'unixepoch')) AS distinct_delivery_days
FROM deliveries d
GROUP BY d.driver_id
```

---

**Skill `driver_average_daily_deliveries`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `driver_id` |
| output columns | `driver_id`, `avg_daily_deliveries` |
| source tables | `driver_deliveries_events` |
| depends_on (builds on) | `driver_deliveries_events`, `driver_daily_counts`, `driver_totals_and_days` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each driver, compute the average daily deliveries as total_deliveries divided by distinct_delivery_days, and exclude drivers with zero distinct_delivery_days. (Final sorting and top-5 selection are applied outside this sub-goal.)_

```sql
SELECT
  d.driver_id AS driver_id,
  CAST(dt.total_deliveries AS FLOAT) / dt.distinct_delivery_days AS avg_daily_deliveries
FROM
  (SELECT
     driver_id,
     COUNT(delivery_id) AS total_deliveries,
     COUNT(DISTINCT delivery_date) AS distinct_delivery_days
   FROM
     driver_deliveries_events
   GROUP BY
     driver_id
  ) AS dt
JOIN
  (SELECT DISTINCT driver_id FROM driver_deliveries_events) AS d
  ON d.driver_id = dt.driver_id
WHERE
  dt.distinct_delivery_days > 0
```

---
