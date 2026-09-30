# Skill graph — `bank_sales_trading` (8 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customer_transactions` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 4 |

_Task: For each customer and for each calendar month in the requested range, compute the account closing balance at the end of that month, the change in balance compared to the previous month, and the _

```sql
SELECT
  ct.customer_id,
  -- month_year in YYYY-MM format derived from txn_date
  substr(ct.txn_date,1,7) AS month_year,
  ct.txn_date AS txn_date,
  ct.txn_type,
  ct.txn_amount
FROM customer_transactions ct
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `shopping_cart_page_hierarchy`, `shopping_cart_events` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute, for each product, counts of user events showing how many times the product page was viewed, how many times the product was added to the shopping cart, how many times the product was lef_

```sql
SELECT
  hp.product_id,
  hp.page_id,
  he.event_type,
  he.visit_id,
  he.cookie_id,
  he.event_time
FROM
  shopping_cart_page_hierarchy AS hp
JOIN
  shopping_cart_events AS he
  ON hp.page_id = he.page_id
WHERE
  hp.page_id NOT IN (1, 2, 12, 13)
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `interest_metrics`, `interest_map` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | Identify the top 10 and bottom 10 interest categories based on their highest composition values across all months. For each category, display the time(MM-YYYY), interest name, and the composition value |
| counter_examples | 0 |

_Task: For each month from September 2018 through August 2019, compute for every interest the average composition divided by the index (i.e., composition / index), identify the interest with the highes_

```sql
SELECT
  interest_metrics._month AS month_number,
  interest_metrics._year AS year_number,
  interest_map.id AS interest_id,
  interest_map.interest_name,
  interest_metrics.composition,
  interest_metrics.index_value
FROM interest_metrics
JOIN interest_map
  ON interest_metrics.interest_id = interest_map.id
WHERE interest_metrics._year IN (2018.0, 2019.0)
  AND interest_metrics.month_year IS NOT NULL
  AND interest_metrics.index_value IS NOT NULL
  AND interest_metrics.index_value != 0
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `bitcoin_transactions`, `bitcoin_members` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each region and year, compute the annual average purchase price per Bitcoin as (total dollar amount spent in that region and year) divided by (total quantity of Bitcoin purchased in that reg_

```sql
SELECT
  bm.member_id,
  bm.region AS region,
  bt.txn_date,
  bt.txn_time,
  bt.txn_type,
  bt.ticker,
  bt.quantity,
  bt.percentage_fee
FROM
  bitcoin_transactions bt
JOIN
  bitcoin_members bm
  ON bt.member_id = bm.member_id
WHERE
  bt.txn_type = 'BUY'
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `bitcoin_prices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each ticker in the bitcoin_prices table, compute the daily percentage change in trading volume for each date from 2021-08-01 through 2021-08-10 inclusive, after normalizing volume strings so_

```sql
SELECT
  ticker,
  market_date,
  volume
FROM bitcoin_prices
WHERE market_date >= '01-08-2021' AND market_date <= '10-08-2021'
```

---

**Skill `chunk_view_0_5`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `veg_loss_rate_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute summary statistics for 'veg whsle' items' loss rates: overall average loss rate and counts of items whose loss rate is below one standard deviation below the average, within one standard_

```sql
SELECT
  item_code,
  item_name,
  "loss_rate_%"
FROM
  veg_loss_rate_df
WHERE
  item_code IS NOT NULL
```

---

**Skill `chunk_view_0_6`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `veg_whsle_df`, `veg_cat`, `veg_loss_rate_df`, `veg_txn_df` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute year-by-year (2020 through 2023) per-category financial summary for veg whsle data, producing for each year and each category the requested aggregated metrics rounded to two decimal plac_

```sql
SELECT
  vw.whsle_date,
  vw.item_code,
  vw."whsle_px_rmb-kg",
  vc.category_code,
  vc.category_name,
  vlr."loss_rate_%",
  vt."unit_selling_px_rmb/kg",
  vt."txn_date" AS sale_txn_date,
  vw."index" AS vw_index,
  vc."index" AS vc_index,
  vlr."index" AS vlr_index,
  vt."index" AS vt_index
FROM veg_whsle_df vw
LEFT JOIN veg_cat vc
  ON vw.item_code = vc.item_code
LEFT JOIN veg_loss_rate_df vlr
  ON vw.item_code = vlr.item_code
LEFT JOIN veg_txn_df vt
  ON vw.item_code = vt.item_code
WHERE
  vw.whsle_date IS NOT NULL
  AND (vw."whsle_px_rmb-kg" IS NOT NULL OR vlr."loss_rate_%" IS NOT NULL OR vt."unit_selling_px_rmb/kg" IS NOT NULL)
```

---

**Skill `chunk_view_0_7`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `cleaned_weekly_sales` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: For each of the years 2018, 2019, and 2020, compute the percentage change in total sales between the four-week period immediately preceding June 15 (the four weeks that end the day before June 1_

```sql
SELECT
  cleaned_weekly_sales.calendar_year AS year,
  cleaned_weekly_sales.week_date_formatted AS week_date_formatted,
  cleaned_weekly_sales.week_date AS week_date,
  cleaned_weekly_sales.sales,
  cleaned_weekly_sales.week_number,
  cleaned_weekly_sales.month_number
FROM cleaned_weekly_sales
WHERE cleaned_weekly_sales.calendar_year IN (2018, 2019, 2020)
  -- include all weeks for those years so downstream logic can identify the 4-week pre/post windows around June 15
```

---
