# Skill graph — `bank_sales_trading` (2 skills)

**Skill `customer_monthly_changes`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `monthly_balance_change` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_cumulative` |
| validated_on | — |
| counter_examples | 0 |

_aggregates raw transaction amounts by customer and calendar month to compute the net balance change for each period_

```sql
SELECT customer_id, strftime('%Y-%m', txn_date) AS month, SUM(txn_amount) AS monthly_balance_change FROM customer_transactions GROUP BY customer_id, strftime('%Y-%m', txn_date)
```

---

**Skill `customer_monthly_cumulative`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `monthly_balance_change`, `monthly_cumulative_balance` |
| source tables | `customer_monthly_changes` |
| depends_on (builds on) | `customer_monthly_changes` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_generates a complete sequence of months per customer to fill activity gaps, joins with monthly changes, and computes the running total balance using a window function_

```sql
WITH RECURSIVE month_gen AS (
    SELECT customer_id, month FROM customer_monthly_changes
    UNION ALL
    SELECT customer_id, date(month, '+1 month') FROM month_gen
    WHERE date(month, '+1 month') <= (SELECT MAX(month) FROM customer_monthly_changes WHERE customer_id = month_gen.customer_id)
)
SELECT
    m.customer_id,
    m.month,
    COALESCE(c.monthly_balance_change, 0) as monthly_balance_change,
    SUM(COALESCE(c.monthly_balance_change, 0)) OVER (PARTITION BY m.customer_id ORDER BY m.month) as monthly_cumulative_balance
FROM month_gen m
LEFT JOIN customer_monthly_changes c ON m.customer_id = c.customer_id AND m.month = c.month
```

---
