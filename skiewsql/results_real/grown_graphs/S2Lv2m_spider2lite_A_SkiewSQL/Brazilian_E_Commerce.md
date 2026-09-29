# Skill graph — `Brazilian_E_Commerce` (5 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `olist_orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | What is the highest monthly delivered orders volume in the year with the lowest annual delivered orders volume among 2016, 2017, and 2018? |
| counter_examples | 0 |

_Task: Compute a report that shows, for each month (January through December), the number of delivered orders in that month for each of the years 2016, 2017, and 2018, with one row per month and one co_

```sql
SELECT
  o.order_id,
  o.order_status,
  o.order_delivered_customer_date,
  -- extract year and month for later aggregation
  CAST(strftime('%Y', o.order_delivered_customer_date) AS INTEGER) AS delivered_year,
  CAST(strftime('%m', o.order_delivered_customer_date) AS INTEGER) AS delivered_month
FROM
  olist_orders o
WHERE
  o.order_delivered_customer_date IS NOT NULL
  AND o.order_status = 'delivered'
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `olist_customers`, `olist_orders`, `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Find the top three distinct customer_unique_id values with the highest count of orders whose status is 'delivered', and for each of these customers return that customer_unique_id, the count of t_

```sql
SELECT
  c.customer_id,
  c.customer_unique_id,
  c.customer_city,
  c.customer_state,
  o.order_id,
  o.order_status,
  op.payment_value
FROM olist_customers c
JOIN olist_orders o
  ON c.customer_id = o.customer_id
LEFT JOIN olist_order_payments op
  ON o.order_id = op.order_id
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `olist_orders`, `olist_order_items`, `olist_products`, `olist_customers`, `olist_order_payments`, `olist_order_reviews` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For cities that have at least one delivered order, compute each city's total payments summed over all payments for that city, then select the five cities with the smallest summed payments; final_

```sql
SELECT
  o.order_id,
  o.customer_id,
  o.order_status,
  o.order_purchase_timestamp,
  oi.order_item_id,
  oi.product_id,
  oi.seller_id,
  oi.price AS item_price,
  oi.freight_value,
  p.product_id AS product_product_id,
  p.product_category_name AS product_category_name,
  c.customer_id AS customer_customer_id,
  c.customer_zip_code_prefix,
  c.customer_city,
  c.customer_state,
  pay.payment_sequential,
  pay.payment_type,
  pay.payment_installments,
  pay.payment_value,
  r.review_id,
  r.review_score
FROM olist_orders o
LEFT JOIN olist_order_items oi ON o.order_id = oi.order_id
LEFT JOIN olist_products p ON oi.product_id = p.product_id
LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
LEFT JOIN olist_order_payments pay ON o.order_id = pay.order_id
LEFT JOIN olist_order_reviews r ON o.order_id = r.order_id
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `olist_products`, `olist_order_items`, `olist_orders`, `olist_order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For each product category, find the payment method that has the highest number of payments within that category, take that payment method's total number of payments for the category, then comput_

```sql
SELECT
  p.product_category_name,
  oi.order_id,
  op.payment_type,
  op.payment_value,
  op.payment_sequential,
  -- keep counts per (category, payment_type) possible later aggregation
  -- include product and order item identifiers to join/order aggregation later
  p.product_id,
  oi.seller_id,
  o.customer_id
FROM olist_products p
JOIN olist_order_items oi
  ON p.product_id = oi.product_id
JOIN olist_orders o
  ON oi.order_id = o.order_id
JOIN olist_order_payments op
  ON o.order_id = op.order_id
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `olist_geolocation` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Determine which two consecutive rows (cities) in the olist_geolocation table — when rows are ordered by geolocation_state, then geolocation_city, then geolocation_zip_code_prefix, then geolocati_

```sql
SELECT
  g.geolocation_zip_code_prefix,
  g.geolocation_lat,
  g.geolocation_lng,
  g.geolocation_city,
  g.geolocation_state,
  LAG(g.geolocation_zip_code_prefix) OVER (
    ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat ASC, g.geolocation_lng ASC
  ) AS prev_geolocation_zip_code_prefix,
  LAG(g.geolocation_lat) OVER (
    ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat ASC, g.geolocation_lng ASC
  ) AS prev_geolocation_lat,
  LAG(g.geolocation_lng) OVER (
    ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat ASC, g.geolocation_lng ASC
  ) AS prev_geolocation_lng,
  LAG(g.geolocation_city) OVER (
    ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat ASC, g.geolocation_lng ASC
  ) AS prev_geolocation_city,
  LAG(g.geolocation_state) OVER (
    ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat ASC, g.geolocation_lng ASC
  ) AS prev_geolocation_state
FROM olist_geolocation g
ORDER BY g.geolocation_state ASC, g.geolocation_city ASC, g.geolocation_zip_code_prefix ASC, g.geolocation_lat ASC, g.geolocation_lng ASC
```

---
