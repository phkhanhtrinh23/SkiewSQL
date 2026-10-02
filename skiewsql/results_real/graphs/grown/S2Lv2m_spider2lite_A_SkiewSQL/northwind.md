# Skill graph — `northwind` (2 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customers`, `orders`, `order_details`, `customergroupthreshold` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For customers who placed at least one order in 1998, compute each customer's total spending in 1998 as the sum over all ordered products of (unit price * quantity) with discounts ignored. Then a_

```sql
SELECT
  c.customerid,
  c.companyname,
  o.orderid,
  o.orderdate,
  od.productid,
  od.unitprice,
  od.quantity,
  (od.unitprice * od.quantity) AS line_amount,
  -- customer total spending in 1998 will be aggregated later; include keys to join thresholds
  cg.groupname,
  cg.rangebottom,
  cg.rangetop
FROM customers c
JOIN orders o
  ON c.customerid = o.customerid
JOIN order_details od
  ON o.orderid = od.orderid
LEFT JOIN customergroupthreshold cg
  -- no direct key to join here; include threshold table rows so downstream logic can assign ranges
  ON 1=1
WHERE o.orderdate BETWEEN DATE('1998-01-01') AND DATE('1998-12-31')
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `employees`, `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For employees who have more than 50 total orders, compute each employee's number of late orders (orders with shipped date on or after the required date) and the percentage of that employee's ord_

```sql
SELECT
  e.employeeid,
  o.orderid,
  o.orderdate,
  o.requireddate,
  o.shippeddate
FROM employees e
JOIN orders o ON e.employeeid = o.employeeid
```

---
