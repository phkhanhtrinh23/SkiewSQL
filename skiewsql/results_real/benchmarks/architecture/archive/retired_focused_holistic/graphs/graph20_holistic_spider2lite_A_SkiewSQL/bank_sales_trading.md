# Skill graph — `bank_sales_trading` (1 skills)

**Skill `focused_whole_view`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 10 |

_Task: Calculate the total balance for each month, using the previous month's balance as a baseline, replacing negative balances with zero, and excluding the first month's data from the final result. R_

```sql
SELECT
    'Month' AS Month,
    COALESCE(SUM(CASE WHEN T2.week_number = T1.week_number - 1 THEN T1.sales ELSE 0 END), 0) AS "Total Balance"
FROM cleaned_weekly_sales AS T1
INNER JOIN cleaned_weekly_sales AS T2
ON T1.week_number = T2.week_number
WHERE T2.week_number > 1
```

---
