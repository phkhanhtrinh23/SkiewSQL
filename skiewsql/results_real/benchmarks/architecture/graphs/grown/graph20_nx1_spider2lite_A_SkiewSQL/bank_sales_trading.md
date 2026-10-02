# Skill graph — `bank_sales_trading` (2 skills)

**Skill `chunk_view_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Generate a monthly summary of customer bank account balances, including monthly changes and cumulative balances, for all customers, even those with no transactions in a specific month. Required _

```sql
SELECT
    'cleaned_weekly_sales'.week_date_formatted,
    'cleaned_weekly_sales'.sales,
    0.00
FROM cleaned_weekly_sales
```

---

**Skill `chunk_view_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `shopping_cart_campaign_identifier` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Generate a monthly summary of customer bank account balances, including monthly changes and cumulative balances, for all customers, even those with no transactions in a specific month. Required _

```sql
SELECT
    'shopping_cart_campaign_identifier'.campaign_name,
    'shopping_cart_campaign_identifier'.start_date,
    'shopping_cart_campaign_identifier'.end_date,
    SUM('shopping_cart_campaign_identifier'.products)
FROM
    shopping_cart_campaign_identifier
limit 0
```

---
