# Skill graph — `E_commerce` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `orders`, `order_items`, `products` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute predicted daily toy sales for each date December 5, 2018 through December 8, 2018 using a simple linear regression model trained on the provided historical daily sales data from January _

```sql
SELECT
  orders.order_purchase_timestamp AS order_purchase_timestamp,
  orders.order_id AS order_id,
  order_items.order_item_id AS order_item_id,
  order_items.product_id AS product_id,
  products.product_category_name AS product_category_name,
  products.product_category_name AS product_category_name_duplicate,
  products.product_weight_g AS product_weight_g,
  products.product_photos_qty AS product_photos_qty
FROM orders
JOIN order_items ON orders.order_id = order_items.order_id
JOIN products ON order_items.product_id = products.product_id
WHERE orders.order_purchase_timestamp IS NOT NULL
```

---
