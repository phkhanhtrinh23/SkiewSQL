# Skill graph — `electronic_sales` (2 skills)

**Skill `seller_performance_metrics`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `seller_id` |
| output columns | `seller_id`, `total_sales`, `avg_item_price`, `avg_review_score`, `avg_packing_time`, `products_sold_count` |
| source tables | `order_items`, `orders`, `order_reviews` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregates transaction-level records per seller to compute total revenue, average item price, average review score, and average packing time, along with the total count of products sold._

```sql
SELECT
    oi.seller_id,
    SUM(oi.price) AS total_sales,
    AVG(oi.price) AS avg_item_price,
    AVG(rev.review_score) AS avg_review_score,
    AVG(julianday(o.order_delivered_carrier_date) - julianday(o.order_purchase_timestamp)) AS avg_packing_time,
    COUNT(oi.product_id) AS products_sold_count
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
LEFT JOIN order_reviews rev ON o.order_id = rev.order_id
GROUP BY oi.seller_id
```

---

**Skill `seller_category_ranking`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `seller_id`, `product_category_name_english` |
| output columns | `seller_id`, `category_name_en`, `category_sales_volume`, `category_rank` |
| source tables | `order_items`, `products`, `product_category_name_translation` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_ranks product categories by total sales volume per seller to identify the highest-selling category for each vendor._

```sql
SELECT oi.seller_id, pct.product_category_name_english AS category_name_en, SUM(oi.price) AS category_sales_volume, RANK() OVER (PARTITION BY oi.seller_id ORDER BY SUM(oi.price) DESC) AS category_rank FROM order_items oi JOIN products p ON oi.product_id = p.product_id JOIN product_category_name_translation pct ON p.product_category_name = pct.product_category_name GROUP BY oi.seller_id, pct.product_category_name_english
```

---
