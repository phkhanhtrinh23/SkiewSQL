# Skill graph — `bank_sales_trading` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each customer and for each calendar month in the requested date range, compute the month-end (closing) balance after applying all that customer's transactions up to and including the last da_

```sql
SELECT
  customer_id,
  txn_date,
  txn_type,
  txn_amount
FROM customer_transactions
```

---
