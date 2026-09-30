# Skill graph — `electronic_sales` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `order_items`, `sellers`, `products`, `orders`, `order_reviews`, `order_payments`, `customers`, `product_category_name_translation`, `geolocation` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute a comprehensive performance report for sellers who have sold more than 100 products, showing per-seller total sales, average item price, average review score, and average packing time, a_

```sql
SELECT
  s.seller_id,
  s.seller_zip_code_prefix,
  s.seller_city,
  s.seller_state,
  oi.order_id,
  oi.order_item_id,
  oi.product_id,
  oi.price,
  oi.freight_value,
  oi.shipping_limit_date,
  oi.seller_id AS order_item_seller_id,
  p.product_category_name,
  p.product_name_lenght,
  p.product_description_lenght,
  p.product_photos_qty,
  p.product_weight_g,
  p.product_length_cm,
  p.product_height_cm,
  p.product_width_cm,
  o.customer_id,
  o.order_status,
  o.order_purchase_timestamp,
  o.order_approved_at,
  o.order_delivered_carrier_date,
  o.order_delivered_customer_date,
  o.order_estimated_delivery_date,
  orv.review_id,
  orv.review_score,
  orv.review_creation_date,
  orv.review_answer_timestamp,
  op.payment_sequential,
  op.payment_type,
  op.payment_installments,
  op.payment_value,
  c.customer_unique_id,
  c.customer_zip_code_prefix,
  c.customer_city,
  c.customer_state,
  pcnt.product_category_name_english,
  g.geolocation_zip_code_prefix,
  g.geolocation_lat,
  g.geolocation_lng,
  g.geolocation_city,
  g.geolocation_state
FROM order_items oi
JOIN sellers s
  ON oi.seller_id = s.seller_id
LEFT JOIN products p
  ON oi.product_id = p.product_id
LEFT JOIN orders o
  ON oi.order_id = o.order_id
LEFT JOIN order_reviews orv
  ON oi.order_id = orv.order_id
LEFT JOIN order_payments op
  ON oi.order_id = op.order_id
LEFT JOIN customers c
  ON o.customer_id = c.customer_id
LEFT JOIN product_category_name_translation pcnt
  ON p.product_category_name = pcnt.product_category_name
LEFT JOIN geolocation g
  ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
```

---
