# Skill graph — `complex_oracle` (1 skills)

**Skill `city_product_quarter_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `cust_city`, `prod_name`, `calendar_quarter_desc` |
| output columns | `city`, `product`, `quarter`, `total_sales` |
| source tables | `sales`, `customers`, `products`, `times` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_total non-promotional sales grouped by city, product, and quarter_

```sql
SELECT c.cust_city AS city, p.prod_name AS product, t.calendar_quarter_desc AS quarter, SUM(s.amount_sold) AS total_sales FROM sales s JOIN customers c ON s.cust_id = c.cust_id JOIN products p ON s.prod_id = p.prod_id JOIN times t ON s.time_id = t.time_id WHERE s.promo_id IS NULL GROUP BY c.cust_city, p.prod_name, t.calendar_quarter_desc
```

---
