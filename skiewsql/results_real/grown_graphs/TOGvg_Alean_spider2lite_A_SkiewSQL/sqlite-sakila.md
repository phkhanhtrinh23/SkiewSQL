# Skill graph — `sqlite-sakila` (2 skills)

**Skill `customer_monthly_changes`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `payment_amount`, `monthly_change` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `avg_monthly_change_per_customer` |
| validated_on | — |
| counter_examples | 0 |

_payment records ordered by customer and month with the difference between current and previous month's payment amounts_

```sql
SELECT
    customer_id,
    strftime('%Y-%m', payment_date) AS month,
    SUM(amount) AS payment_amount,
    SUM(amount) - LAG(SUM(amount)) OVER (PARTITION BY customer_id ORDER BY strftime('%Y-%m', payment_date)) AS monthly_change
FROM payment
GROUP BY customer_id, strftime('%Y-%m', payment_date)
```

---

**Skill `avg_monthly_change_per_customer`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `avg_monthly_change` |
| source tables | `customer_monthly_changes` |
| depends_on (builds on) | `customer_monthly_changes` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_average of the monthly payment changes grouped by customer_

```sql
SELECT customer_id, AVG(monthly_change) AS avg_monthly_change
FROM customer_monthly_changes
GROUP BY customer_id
```

---
