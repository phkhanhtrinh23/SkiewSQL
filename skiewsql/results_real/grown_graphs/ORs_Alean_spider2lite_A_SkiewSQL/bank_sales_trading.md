# Skill graph — `bank_sales_trading` (1 skills)

**Skill `customer_monthly_net`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `monthly_net` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All customer-month combinations within the overall data date range, with net transaction amount for each month (zero if no transactions)._

```sql
SELECT
    c.customer_id,
    m.month,
    COALESCE(a.monthly_net, 0) AS monthly_net
FROM (
    SELECT DISTINCT customer_id
    FROM customer_transactions
) c
CROSS JOIN (
    SELECT DISTINCT strftime('%Y-%m', date(REPLACE(txn_date, '/', '-'))) AS month
    FROM customer_transactions
) m
LEFT JOIN (
    SELECT
        customer_id,
        strftime('%Y-%m', date(REPLACE(txn_date, '/', '-'))) AS month,
        SUM(CASE WHEN txn_type = 'deposit' THEN txn_amount ELSE -txn_amount END) AS monthly_net
    FROM customer_transactions
    GROUP BY customer_id, strftime('%Y-%m', date(REPLACE(txn_date, '/', '-')))
) a
    ON c.customer_id = a.customer_id
   AND m.month = a.month
```

---
