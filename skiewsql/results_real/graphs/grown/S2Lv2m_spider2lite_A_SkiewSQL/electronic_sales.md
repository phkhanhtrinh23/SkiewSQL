# Skill graph — `electronic_sales` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `order_items`, `orders`, `order_reviews`, `products`, `sellers`, `product_category_name_translation`, `order_payments` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Produce a comprehensive performance report for sellers who have sold more than 100 products, computing each seller's total sales, average item price, average review score, and average packing ti_

```sql
SELECT
  oi.seller_id,
  oi.order_id,
  oi.order_item_id,
  oi.product_id,
  oi.price,
  oi.freight_value,
  oi.shipping_limit_date,
  o.customer_id,
  o.order_purchase_timestamp,
  orv.review_id,
  orv.review_score,
  orv.review_creation_date,
  p.product_category_name,
  p.product_name_lenght,
  p.product_weight_g,
  s.seller_zip_code_prefix,
  s.seller_city,
  s.seller_state,
  pc.product_category_name_english,
  op.payment_sequential,
  op.payment_type,
  op.payment_installments,
  op.payment_value
FROM order_items oi
LEFT JOIN orders o
  ON oi.order_id = o.order_id
LEFT JOIN order_reviews orv
  ON oi.order_id = orv.order_id
LEFT JOIN products p
  ON oi.product_id = p.product_id
LEFT JOIN sellers s
  ON oi.seller_id = s.seller_id
LEFT JOIN product_category_name_translation pc
  ON p.product_category_name = pc.product_category_name
LEFT JOIN order_payments op
  ON oi.order_id = op.order_id
```

---
