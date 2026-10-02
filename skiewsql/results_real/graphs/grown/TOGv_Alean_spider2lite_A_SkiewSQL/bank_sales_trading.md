# Skill graph — `bank_sales_trading` (2 skills)

**Skill `monthly_account_changes`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer`, `month`, `monthly_change` |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_month_balance_sequence` |
| validated_on | — |
| counter_examples | 0 |

_aggregates raw account activity to compute net monthly change per customer_

```sql
SELECT customer_id AS customer, strftime('%Y-%m', txn_date) AS month, SUM(txn_amount) AS monthly_change FROM customer_transactions GROUP BY customer_id, strftime('%Y-%m', txn_date)
```

---

**Skill `customer_month_balance_sequence`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer`, `month` |
| output columns | `customer`, `month`, `monthly_change`, `cumulative_balance` |
| source tables | `monthly_account_changes` |
| depends_on (builds on) | `monthly_account_changes` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_expands to full calendar months per customer, joins with changes, carries forward balances, and computes cumulative totals_

```sql
SELECT customer, month, monthly_change, COALESCE(SUM(monthly_change) OVER (PARTITION BY customer ORDER BY month), 0) AS cumulative_balance FROM monthly_account_changes
```

---
