# Skill graph — `northwind` (2 skills)

**Skill `customer_spending_1998`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customerid` |
| output columns | `customer_id`, `total_spending_1998` |
| source tables | `orders`, `order_details` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `spending_group_metrics` |
| validated_on | — |
| counter_examples | 0 |

_one row per customer who placed orders in 1998, containing their total spending calculated as the sum of unit price multiplied by quantity across all order items while explicitly ignoring discount values_

```sql
SELECT o.customerid AS customer_id, SUM(od.unitprice * od.quantity) AS total_spending_1998
FROM orders o
JOIN order_details od ON o.orderid = od.orderid
GROUP BY o.customerid
```

---

**Skill `spending_group_metrics`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `groupname` |
| output columns | `spending_group`, `customer_count`, `percentage_of_total_1998_customers` |
| source tables | `customergroupthreshold` |
| depends_on (builds on) | `customer_spending_1998` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_one row per spending group, containing the count of customers assigned to that group and their percentage relative to the total 1998 customer count, derived by applying external spending thresholds to the per-customer spending totals_

```sql
SELECT 
    cgt.groupname AS spending_group,
    COUNT(cs.customer_id) AS customer_count,
    CAST(COUNT(cs.customer_id) AS REAL) * 100.0 / (SELECT COUNT(*) FROM customer_spending_1998) AS percentage_of_total_1998_customers
FROM customergroupthreshold cgt
JOIN customer_spending_1998 cs ON cs.total_spending_1998 >= cgt.rangebottom AND cs.total_spending_1998 < cgt.rangetop
GROUP BY cgt.groupname
```

---
