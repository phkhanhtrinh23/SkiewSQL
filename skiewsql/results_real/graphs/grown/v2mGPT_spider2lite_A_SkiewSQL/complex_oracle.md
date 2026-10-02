# Skill graph — `complex_oracle` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `sales`, `customers`, `products` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For U.S. cities, identify those cities where total sales excluding promotions increased by at least 20% from Q4 2019 to Q4 2020. Within each such city, rank products by their combined sales (exc_

```sql
SELECT
  s.cust_id,
  c.cust_city,
  s.prod_id,
  p.prod_name,
  s.time_id,
  s.promo_id,
  s.quantity_sold,
  s.amount_sold
FROM sales s
JOIN customers c ON s.cust_id = c.cust_id
JOIN products p ON s.prod_id = p.prod_id
```

---
