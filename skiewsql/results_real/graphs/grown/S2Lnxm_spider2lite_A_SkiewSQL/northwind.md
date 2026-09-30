# Skill graph — `northwind` (8 skills)

**Skill `orders_1998`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `order_id`, `customer_id`, `order_date` |
| source tables | `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `order_lines_1998` |
| validated_on | — |
| counter_examples | 0 |

_All orders placed in the year 1998 (order rows filtered to the 1998 date range)._

```sql
SELECT
  orderid AS order_id,
  customerid AS customer_id,
  orderdate AS order_date
FROM orders
WHERE orderdate >= '1998-01-01' AND orderdate < '1999-01-01'
```

---

**Skill `order_lines_1998`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `order_line_id` |
| output columns | `order_id`, `customer_id`, `order_line_id`, `unit_price`, `quantity` |
| source tables | `order_details`, `orders_1998` |
| depends_on (builds on) | `orders_1998` |
| depended-on by (builds on this) | `customer_spend_1998` |
| validated_on | — |
| counter_examples | 0 |

_Order line items for the 1998 orders, joined to their orders so each line is associated with the customer and constrained to 1998. Include unit price and quantity for each line (no discounts applied)._

```sql
SELECT
  od.orderid AS order_id,
  o.customer_id AS customer_id,
  rowid AS order_line_id,
  od.unitprice AS unit_price,
  od.quantity AS quantity
FROM order_details od
JOIN orders_1998 o ON od.orderid = o.order_id
```

---

**Skill `customer_spend_1998`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `total_spend_1998` |
| source tables | `order_lines_1998` |
| depends_on (builds on) | `order_lines_1998` |
| depended-on by (builds on this) | `spend_group_counts` |
| validated_on | — |
| counter_examples | 0 |

_Total 1998 spending per customer computed as the sum over their 1998 order lines of (unit_price * quantity). One row per customer who had at least one 1998 order line._

```sql
SELECT
  ol.customer_id AS customer_id,
  SUM(ol.unit_price * ol.quantity) AS total_spend_1998
FROM order_lines_1998 ol
GROUP BY ol.customer_id
```

---

**Skill `spend_group_counts`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `rangebottom`, `groupname` |
| output columns | `spending_group_id`, `spending_group_name`, `customers_in_group`, `percent_of_customers` |
| source tables | `customergroupthreshold`, `customer_spend_1998` |
| depends_on (builds on) | `customer_spend_1998` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Assign each customer to a spending group using the customer group thresholds, then count distinct customers per spending group and include each group's share of the total distinct customers who placed orders in 1998._

```sql
SELECT
  cgt.rangebottom AS spending_group_id,
  cgt.groupname AS spending_group_name,
  COUNT(DISTINCT cs.customer_id) AS customers_in_group,
  CASE WHEN total.total_customers = 0 THEN 0.0
       ELSE CAST(COUNT(DISTINCT cs.customer_id) AS REAL) / total.total_customers
  END AS percent_of_customers
FROM customergroupthreshold cgt
LEFT JOIN customer_spend_1998 cs
  ON cs.total_spend_1998 >= cgt.rangebottom
  AND cs.total_spend_1998 <= cgt.rangetop
CROSS JOIN (
  SELECT COUNT(DISTINCT customer_id) AS total_customers
  FROM customer_spend_1998
) AS total
GROUP BY cgt.rangebottom, cgt.groupname
```

---

**Skill `employee_orders`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `employee_id`, `order_id`, `order_date`, `required_date`, `shipped_date` |
| source tables | `orders`, `employees` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `employee_order_counts` |
| validated_on | — |
| counter_examples | 0 |

_All orders attached to each employee (who placed them), including order identifiers and the relevant date fields needed to determine lateness._

```sql
SELECT
  e.employeeid AS employee_id,
  o.orderid AS order_id,
  o.orderdate AS order_date,
  o.requireddate AS required_date,
  o.shippeddate AS shipped_date
FROM orders o
JOIN employees e
  ON o.employeeid = e.employeeid
```

---

**Skill `order_lateness_flag`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `order_id` |
| output columns | `employee_id`, `order_id`, `is_late` |
| source tables | `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `employee_order_counts` |
| validated_on | — |
| counter_examples | 0 |

_Normalize orders to add a boolean/flag indicating whether each order is late (shipped_date >= required_date) and ensure date fields are canonicalized for comparison._

```sql
SELECT
  o.employeeid AS employee_id,
  o.orderid AS order_id,
  CASE
    WHEN trim(o.shippeddate) = '' OR o.shippeddate IS NULL THEN 0
    WHEN trim(o.requireddate) = '' OR o.requireddate IS NULL THEN 0
    WHEN date(o.shippeddate) >= date(o.requireddate) THEN 1
    ELSE 0
  END AS is_late
FROM orders o
```

---

**Skill `employee_order_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `employee_id` |
| output columns | `employee_id`, `total_orders`, `late_orders` |
| source tables | `employee_orders`, `order_lateness_flag` |
| depends_on (builds on) | `employee_orders`, `order_lateness_flag` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Per-employee aggregated counts: total orders and total late orders (sum of the is_late flag)._

```sql
SELECT
  eo.employee_id AS employee_id,
  COUNT(eo.order_id) AS total_orders,
  SUM(CASE WHEN olf.is_late IS NULL THEN 0 ELSE (olf.is_late) END) AS late_orders
FROM
  employee_orders eo
LEFT JOIN
  order_lateness_flag olf
ON
  eo.employee_id = olf.employee_id
  AND eo.order_id = olf.order_id
GROUP BY
  eo.employee_id
```

---

**Skill `employee_late_rate`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `employeeid` |
| output columns | `employee_id`, `total_orders`, `late_orders`, `late_percentage` |
| source tables | `employees`, `orders` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute per-employee late-order percentage (late_orders / total_orders * 100) and retain employees for downstream filtering/sorting. (This step does not apply the final >50 filter or top-3 limit.)_

```sql
SELECT
  e.employeeid AS employee_id,
  COUNT(o.orderid) AS total_orders,
  SUM(CASE WHEN o.shippeddate IS NOT NULL AND o.shippeddate > o.requireddate THEN 1 ELSE 0 END) AS late_orders,
  CASE
    WHEN COUNT(o.orderid) = 0 THEN 0.0
    ELSE (SUM(CASE WHEN o.shippeddate IS NOT NULL AND o.shippeddate > o.requireddate THEN 1 ELSE 0 END) * 100.0) / COUNT(o.orderid)
  END AS late_percentage
FROM employees e
LEFT JOIN orders o
  ON e.employeeid = o.employeeid
GROUP BY e.employeeid
```

---
