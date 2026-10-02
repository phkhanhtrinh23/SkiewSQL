# Skill graph — `complex_oracle` (3 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `sales`, `customers`, `countries`, `products`, `times`, `promotions`, `costs`, `channels`, `supplementary_demographics` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For U.S. cities that had total sales (excluding promotions) increase by at least 20% from Q4 2019 to Q4 2020, identify within each such city the products whose combined sales (excluding promotio_

```sql
SELECT
  sales.cust_id,
  customers.cust_city,
  sales.prod_id,
  products.prod_name,
  sales.time_id,
  sales.promo_id,
  sales.quantity_sold,
  sales.amount_sold,
  customers.country_id,
  countries.country_name
FROM sales
LEFT JOIN customers ON sales.cust_id = customers.cust_id
LEFT JOIN countries ON customers.country_id = countries.country_id
LEFT JOIN products ON sales.prod_id = products.prod_id
LEFT JOIN times ON sales.time_id = times.time_id
LEFT JOIN promotions ON sales.promo_id = promotions.promo_id
LEFT JOIN costs ON sales.prod_id = costs.prod_id AND sales.time_id = costs.time_id AND sales.channel_id = costs.channel_id AND sales.promo_id = costs.promo_id
LEFT JOIN channels ON sales.channel_id = channels.channel_id
LEFT JOIN supplementary_demographics ON sales.cust_id = supplementary_demographics.cust_id
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `sales`, `times`, `customers`, `countries`, `promotions`, `channels` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Compute the average projected monthly sales in USD for France for 2021 by projecting each product’s 2021 monthly sales using the product-and-month-specific growth rate from 2019 to 2020, convert_

```sql
SELECT
  t.calendar_month_number AS month_number,
  t.calendar_month_desc AS month_desc,
  s.prod_id,
  s.channel_id,
  s.promo_id,
  s.time_id,
  s.amount_sold,
  times.calendar_year,
  times.calendar_month_number,
  c.country_name,
  c.country_id,
  p.promo_total_id,
  ch.channel_total_id
FROM sales s
JOIN times ON s.time_id = times.time_id
JOIN customers cu ON s.cust_id = cu.cust_id
JOIN countries c ON cu.country_id = c.country_id
JOIN promotions p ON s.promo_id = p.promo_id
JOIN channels ch ON s.channel_id = ch.channel_id
JOIN times t ON s.time_id = t.time_id
WHERE c.country_name = 'France'
  AND times.calendar_year IN (2019, 2020)
  AND p.promo_total_id = 1
  AND ch.channel_total_id = 1
  AND s.amount_sold IS NOT NULL
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customers`, `countries`, `sales`, `costs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For December 2021, compute each Italian customer's total monthly profit (profit per line = quantity_sold * (unit_price - unit_cost). Customer monthly profit = sum of those profits over all produ_

```sql
SELECT
  c.cust_id,
  c.country_id,
  co.country_name,
  s.time_id         AS sale_date,
  s.prod_id,
  s.quantity_sold,
  s.amount_sold,
  coalesce(costs.unit_price, costs.unit_price) AS unit_price,
  costs.unit_cost
FROM customers c
JOIN countries co ON c.country_id = co.country_id
JOIN sales s ON c.cust_id = s.cust_id
LEFT JOIN costs ON costs.prod_id = s.prod_id
  AND costs.time_id = s.time_id
  AND costs.promo_id = s.promo_id
  AND costs.channel_id = s.channel_id
WHERE co.country_name = 'Italy'
  AND s.time_id >= DATE('2021-12-01')
  AND s.time_id <= DATE('2021-12-31')
```

---
