# Skill graph — `electronic_sales` (2 skills)

**Skill `seller_performance_metrics`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `seller_id` |
| output columns | `seller`, `total_sales`, `average_item_price`, `average_review_scores`, `average_packing_times` |
| source tables | `sellers`, `order_items`, `orders`, `order_reviews` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregated sales, pricing, review, and fulfillment metrics per seller_

```sql
SELECT s.seller_id AS seller, SUM(oi.price) AS total_sales, AVG(oi.price) AS average_item_price, AVG(ors.review_score) AS average_review_scores, AVG(julianday(o.order_delivered_carrier_date) - julianday(o.order_approved_at)) AS average_packing_times FROM sellers s JOIN order_items oi ON s.seller_id = oi.seller_id JOIN orders o ON oi.order_id = o.order_id JOIN order_reviews ors ON o.order_id = ors.order_id GROUP BY s.seller_id
```

---

**Skill `category_sales_volume`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `product_category_name_english` |
| output columns | `category_name_en`, `total_sales_volume` |
| source tables | `order_items`, `products`, `product_category_name_translation` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_total sales volume grouped by English product category name_

```sql
SELECT 
    pc.product_category_name_english AS category_name_en,
    SUM(oi.price) AS total_sales_volume
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN product_category_name_translation pc ON p.product_category_name = pc.product_category_name
GROUP BY pc.product_category_name_english
```

---
