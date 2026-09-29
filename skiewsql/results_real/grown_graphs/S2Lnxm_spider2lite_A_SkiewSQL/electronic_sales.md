# Skill graph — `electronic_sales` (4 skills)

**Skill `seller_sales_events`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `order_line_id` |
| output columns | `seller_id`, `seller_name`, `product_id`, `category_id`, `category_name_en`, `order_id`, `quantity`, `unit_price`, `line_revenue`, `review_score`, `packing_time` |
| source tables | `order_items`, `sellers`, `products`, `product_category_name_translation`, `orders`, `order_reviews` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `seller_item_level_metrics`, `seller_performance_summary` |
| validated_on | — |
| counter_examples | 0 |

_All individual sales/order line events for sold items, joined to their seller, product, product category, order-level metrics (price, quantity, revenue), review/rating if present, and packing/preparation time if present. This is a denormalized row per sold item instance used as the base event set for later aggregation._

```sql
SELECT
  s.seller_id AS seller_id,
  s.seller_city AS seller_name,
  oi.product_id AS product_id,
  p.product_category_name AS category_id,
  pcat.product_category_name_english AS category_name_en,
  oi.order_id AS order_id,
  oi.order_item_id AS order_line_id,
  1.0 AS quantity,
  oi.price AS unit_price,
  (oi.price * 1.0) AS line_revenue,
  orv.review_score AS review_score,
  (julianday(o.order_delivered_customer_date) - julianday(oi.shipping_limit_date)) * 24.0 AS packing_time
FROM order_items oi
JOIN sellers s
  ON oi.seller_id = s.seller_id
LEFT JOIN products p
  ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation pcat
  ON p.product_category_name = pcat.product_category_name
LEFT JOIN orders o
  ON oi.order_id = o.order_id
LEFT JOIN order_reviews orv
  ON oi.order_id = orv.order_id
```

---

**Skill `seller_item_level_metrics`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `order_id`, `order_line_id` |
| output columns | `seller_id`, `product_id`, `category_id`, `category_name_en`, `order_id`, `quantity`, `unit_price`, `line_revenue`, `review_score`, `packing_time` |
| source tables | `seller_sales_events` |
| depends_on (builds on) | `seller_sales_events` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize and clean numeric fields on each sales event row: ensure unit_price, quantity, line_revenue, review_score, and packing_time are numeric and handle missing/nulls so they are safe for aggregation (e.g., coalesce or flag). Keeps one row per original sales event._

```sql
SELECT
  se.seller_id AS seller_id,
  se.product_id AS product_id,
  se.category_id AS category_id,
  se.category_name_en AS category_name_en,
  se.order_id AS order_id,
  -- ensure quantity is numeric and default to 1 when missing or non-positive
  CASE
    WHEN se.quantity IS NULL THEN 1.0
    WHEN CAST(se.quantity AS REAL) IS NULL THEN 1.0
    WHEN CAST(se.quantity AS REAL) <= 0 THEN 1.0
    ELSE CAST(se.quantity AS REAL)
  END AS quantity,
  -- ensure unit_price is numeric and non-negative, default 0.0
  CASE
    WHEN se.unit_price IS NULL THEN 0.0
    WHEN CAST(se.unit_price AS REAL) IS NULL THEN 0.0
    WHEN CAST(se.unit_price AS REAL) < 0 THEN 0.0
    ELSE CAST(se.unit_price AS REAL)
  END AS unit_price,
  -- ensure line_revenue is numeric; if missing compute quantity * unit_price, else coerce and fallback to computed
  CASE
    WHEN se.line_revenue IS NULL THEN
      (CASE
        WHEN (CASE WHEN se.quantity IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) <= 0 THEN 1.0 ELSE CAST(se.quantity AS REAL) END) IS NULL THEN 0.0
        WHEN (CASE WHEN se.unit_price IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) < 0 THEN 0.0 ELSE CAST(se.unit_price AS REAL) END) IS NULL THEN 0.0
        ELSE (CASE WHEN se.quantity IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) <= 0 THEN 1.0 ELSE CAST(se.quantity AS REAL) END) * (CASE WHEN se.unit_price IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) < 0 THEN 0.0 ELSE CAST(se.unit_price AS REAL) END)
      END)
    WHEN CAST(se.line_revenue AS REAL) IS NULL THEN
      (CASE
        WHEN (CASE WHEN se.quantity IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) <= 0 THEN 1.0 ELSE CAST(se.quantity AS REAL) END) IS NULL THEN 0.0
        WHEN (CASE WHEN se.unit_price IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) < 0 THEN 0.0 ELSE CAST(se.unit_price AS REAL) END) IS NULL THEN 0.0
        ELSE (CASE WHEN se.quantity IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) IS NULL THEN 1.0 WHEN CAST(se.quantity AS REAL) <= 0 THEN 1.0 ELSE CAST(se.quantity AS REAL) END) * (CASE WHEN se.unit_price IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) IS NULL THEN 0.0 WHEN CAST(se.unit_price AS REAL) < 0 THEN 0.0 ELSE CAST(se.unit_price AS REAL) END)
      END)
    WHEN CAST(se.line_revenue AS REAL) < 0 THEN 0.0
    ELSE CAST(se.line_revenue AS REAL)
  END AS line_revenue,
  -- normalize review_score to integer between 1 and 5, NULL if not present or out of range
  CASE
    WHEN se.review_score IS NULL THEN NULL
    WHEN CAST(se.review_score AS INTEGER) IS NULL THEN NULL
    WHEN CAST(se.review_score AS INTEGER) < 1 OR CAST(se.review_score AS INTEGER) > 5 THEN NULL
    ELSE CAST(se.review_score AS INTEGER)
  END AS review_score,
  -- packing_time: ensure numeric non-negative, NULL when missing or invalid
  CASE
    WHEN se.packing_time IS NULL THEN NULL
    WHEN CAST(se.packing_time AS REAL) IS NULL THEN NULL
    WHEN CAST(se.packing_time AS REAL) < 0 THEN NULL
    ELSE CAST(se.packing_time AS REAL)
  END AS packing_time
FROM seller_sales_events se
```

---

**Skill `seller_category_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `seller_id`, `product_category_name` |
| output columns | `seller_id`, `category_id`, `category_name_en`, `category_quantity_sold`, `category_sales_amount` |
| source tables | `order_items`, `products`, `product_category_name_translation` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `seller_performance_summary` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate sales volume (sum of quantity) and sales amount per seller per product category, to identify which category has the highest sales volume for each seller._

```sql
SELECT
  oi.seller_id AS seller_id,
  p.product_category_name AS category_id,
  pct.product_category_name_english AS category_name_en,
  SUM(1) AS category_quantity_sold,
  SUM(oi.price) AS category_sales_amount
FROM
  order_items oi
JOIN
  products p
  ON oi.product_id = p.product_id
LEFT JOIN
  product_category_name_translation pct
  ON p.product_category_name = pct.product_category_name
GROUP BY
  oi.seller_id,
  p.product_category_name
```

---

**Skill `seller_performance_summary`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `seller_id`, `seller_name`, `category_name_en`, `category_quantity_sold` |
| output columns | `seller_id`, `seller_name`, `total_quantity_sold`, `total_sales`, `avg_item_price`, `avg_review_score`, `avg_packing_time`, `top_category_name_en`, `top_category_quantity_sold` |
| source tables | `seller_sales_events`, `seller_category_sales` |
| depends_on (builds on) | `seller_sales_events`, `seller_category_sales` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute per-seller performance aggregates: total quantity sold, total sales (sum revenue), average unit price (weighted or simple as available), average review score, and average packing time. Also join or reference seller_category_sales to attach the top category by quantity per seller and its quantity. This final relation will be filtered to sellers with total quantity > 100 and ordered by total sales._

```sql
SELECT
  sss.seller_id AS seller_id,
  sss.seller_name AS seller_name,
  SUM(sss.quantity) AS total_quantity_sold,
  SUM(sss.line_revenue) AS total_sales,
  CASE WHEN SUM(sss.quantity) = 0 THEN NULL ELSE SUM(sss.line_revenue) * 1.0 / SUM(sss.quantity) END AS avg_item_price,
  AVG(sss.review_score) AS avg_review_score,
  AVG(sss.packing_time) AS avg_packing_time,
  scs_top.category_name_en AS top_category_name_en,
  scs_top.category_quantity_sold AS top_category_quantity_sold
FROM
  seller_sales_events sss
LEFT JOIN (
  SELECT
    seller_id,
    category_name_en,
    category_quantity_sold,
    ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY category_quantity_sold DESC) AS rn
  FROM seller_category_sales
) scs_top ON sss.seller_id = scs_top.seller_id AND scs_top.rn = 1
GROUP BY
  sss.seller_id,
  sss.seller_name,
  scs_top.category_name_en,
  scs_top.category_quantity_sold
HAVING
  SUM(sss.quantity) > 100
```

---
