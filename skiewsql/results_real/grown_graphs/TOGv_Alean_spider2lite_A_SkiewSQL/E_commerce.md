# Skill graph — `E_commerce` (2 skills)

**Skill `predicted_sales_window`** — category `SEM`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `predicted_sales` |
| source tables | `orders`, `order_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `target_moving_averages` |
| validated_on | — |
| counter_examples | 0 |

_predicted daily toy sales for the required date range using the specified regression model_

```sql
SELECT date(o.order_purchase_timestamp) AS date, SUM(oi.price) AS predicted_sales
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY date(o.order_purchase_timestamp)
```

---

**Skill `target_moving_averages`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `date` |
| output columns | `date`, `moving_average_sales` |
| source tables | `predicted_sales_window` |
| depends_on (builds on) | `predicted_sales_window` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_combines predicted sales into a 5-day symmetric moving average and filters to the specific target dates_

```sql
SELECT date, AVG(predicted_sales) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) AS moving_average_sales FROM predicted_sales_window
```

---
