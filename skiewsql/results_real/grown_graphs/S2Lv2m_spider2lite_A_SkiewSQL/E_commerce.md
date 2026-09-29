# Skill graph — `E_commerce` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customers`, `orders`, `order_payments`, `order_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | Could you tell me the number of orders, average payment per order and customer lifespan in weeks of the 3 custumers with the highest average payment per order, where the lifespan is calculated by subtracting the earliest purchase date from the latest purchase date in days, dividing by seven, and if  |
| counter_examples | 0 |

_Task: For each unique customer, using only orders with status equal to 'delivered', compute that customer's Recency (days since their latest purchase as of the maximum purchase timestamp in the datase_

```sql
SELECT
  c.customer_id,
  o.order_id,
  o.order_status,
  o.order_purchase_timestamp,
  op.payment_value,
  oi.price,
  oi.freight_value
FROM customers c
LEFT JOIN orders o
  ON c.customer_id = o.customer_id
LEFT JOIN order_payments op
  ON o.order_id = op.order_id
LEFT JOIN order_items oi
  ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
```

---
