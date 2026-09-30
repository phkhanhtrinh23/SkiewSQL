# Skill graph — `sqlite-sakila` (2 skills)

**Skill `customer_monthly_diffs`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer`, `month` |
| output columns | `customer`, `month`, `payment_amount`, `prev_payment_amount`, `monthly_diff` |
| source tables | `payment`, `customer` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_avg_diff` |
| validated_on | — |
| counter_examples | 0 |

_calculates the month-over-month payment difference for each customer by comparing each month's payment to the previous month's payment_

```sql
SELECT 
    customer_id AS customer,
    month,
    payment_amount,
    LAG(payment_amount) OVER (PARTITION BY customer_id ORDER BY month) AS prev_payment_amount,
    payment_amount - LAG(payment_amount) OVER (PARTITION BY customer_id ORDER BY month) AS monthly_diff
FROM (
    SELECT 
        c.customer_id,
        strftime('%Y-%m', p.payment_date) AS month,
        SUM(p.amount) AS payment_amount
    FROM payment p
    JOIN customer c ON p.customer_id = c.customer_id
    GROUP BY c.customer_id, strftime('%Y-%m', p.payment_date)
)
```

---

**Skill `customer_avg_diff`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer` |
| output columns | `customer`, `avg_monthly_diff` |
| source tables | `customer_monthly_diffs` |
| depends_on (builds on) | `customer_monthly_diffs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_computes the average of the month-over-month payment differences for each customer_

```sql
SELECT customer, AVG(monthly_diff) AS avg_monthly_diff
FROM customer_monthly_diffs
GROUP BY customer
```

---
