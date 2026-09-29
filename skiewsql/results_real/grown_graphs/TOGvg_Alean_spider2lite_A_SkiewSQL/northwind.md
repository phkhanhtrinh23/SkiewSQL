# Skill graph — `northwind` (2 skills)

**Skill `customer_1998_spending`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customerid` |
| output columns | `customer_id`, `total_spending` |
| source tables | `orders`, `order_details` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `spending_group_distribution` |
| validated_on | — |
| counter_examples | 0 |

_total spending per customer derived from 1998 orders, calculated by summing unit price multiplied by quantity while excluding discounts_

```sql
SELECT o.customerid AS customer_id, SUM(od.unitprice * od.quantity) AS total_spending
FROM orders o
JOIN order_details od ON o.orderid = od.orderid
GROUP BY o.customerid
```

---

**Skill `spending_group_distribution`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `groupname` |
| output columns | `spending_group`, `customer_count`, `total_customers` |
| source tables | `customergroupthreshold` |
| depends_on (builds on) | `customer_1998_spending` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_aggregated counts of customers per predefined spending group, including the total number of qualifying customers to enable percentage calculation_

```sql
SELECT 
    t.groupname AS spending_group,
    COUNT(c.customer_id) AS customer_count,
    COUNT(c.customer_id) OVER() AS total_customers
FROM customer_1998_spending c
JOIN customergroupthreshold t 
    ON c.total_spending >= t.rangebottom 
    AND c.total_spending <= t.rangetop
GROUP BY t.groupname
```

---
