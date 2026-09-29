# Skill graph — `sqlite-sakila` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `payment`, `customer` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the customer whose average monthly change in payment amounts is the highest, and return that customer's full name.
Required outputs: full name of the customer (first and last name combined _

```sql
SELECT
  payment.customer_id,
  customer.first_name,
  customer.last_name,
  payment.payment_id,
  payment.amount,
  payment.payment_date,
  payment.last_update
FROM payment
JOIN customer ON customer.customer_id = payment.customer_id
```

---
