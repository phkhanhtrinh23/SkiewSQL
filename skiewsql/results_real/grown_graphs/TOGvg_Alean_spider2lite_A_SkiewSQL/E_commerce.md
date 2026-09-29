# Skill graph — `E_commerce` (2 skills)

**Skill `daily_sales`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `sales` |
| source tables | `orders`, `order_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `predicted_averages` |
| validated_on | — |
| counter_examples | 0 |

_daily toy sales records restricted to the specified training period_

```sql
SELECT date(o.order_purchase_timestamp) AS date, SUM(oi.price) AS sales
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY date(o.order_purchase_timestamp)
```

---

**Skill `predicted_averages`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `moving_average` |
| source tables | `daily_sales` |
| depends_on (builds on) | `daily_sales` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_predicted sales for the target window derived via linear regression, with a 5-day symmetric moving average computed for each date_

```sql
SELECT date, AVG(sales) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) AS moving_average
FROM daily_sales
```

---
