# Skill graph — `sqlite-sakila` (27 skills)

**Skill `payments_normalized`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `payment_id` |
| output columns | `customer_id`, `payment_amount`, `payment_month` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_monthly_totals` |
| validated_on | — |
| counter_examples | 0 |

_Select and normalize payment records: include payment amount and a calendar month derived from the payment date (e.g., year-month). Ensure amount is numeric and month is a canonical year-month value. Keep customer identifier for joining._

```sql
SELECT
  payment.payment_id,
  payment.customer_id AS customer_id,
  CAST(payment.amount AS NUMERIC) AS payment_amount,
  strftime('%Y-%m', payment.payment_date) AS payment_month
FROM payment
```

---

**Skill `customer_monthly_totals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `payment_month` |
| output columns | `customer_id`, `payment_month`, `month_total_amount` |
| source tables | `payments_normalized` |
| depends_on (builds on) | `payments_normalized` |
| depended-on by (builds on this) | `customer_monthly_diffs` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate normalized payments to compute total (or sum) payment amount per customer per calendar month. One row per customer-month representing that month's total payments for the customer._

```sql
SELECT
  pn.customer_id,
  pn.payment_month,
  SUM(pn.payment_amount) AS month_total_amount
FROM
  payments_normalized pn
GROUP BY
  pn.customer_id,
  pn.payment_month
```

---

**Skill `customer_monthly_diffs`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `payment_month` |
| output columns | `customer_id`, `payment_month`, `month_total_amount`, `prev_month_total`, `month_diff` |
| source tables | `customer`, `payment` |
| depends_on (builds on) | `customer_monthly_totals` |
| depended-on by (builds on this) | `customer_avg_monthly_change` |
| validated_on | — |
| counter_examples | 0 |

_For each customer, order their monthly totals by calendar month and compute month-to-month differences (current month total minus previous month total). Keep only rows where a previous month exists so each row represents one month-to-month change._

```sql
SELECT
  t.customer_id,
  t.payment_month,
  t.month_total_amount,
  prev.month_total_amount AS prev_month_total,
  (t.month_total_amount - prev.month_total_amount) AS month_diff
FROM customer_monthly_totals AS t
JOIN customer_monthly_totals AS prev
  ON t.customer_id = prev.customer_id
  AND (
    (strftime('%Y', t.payment_month) = strftime('%Y', prev.payment_month)
     AND (strftime('%m', t.payment_month) = printf('%02d', CAST(strftime('%m', prev.payment_month) AS INTEGER) + 1)))
    OR
    (CAST(strftime('%m', prev.payment_month) AS INTEGER) = 12
     AND CAST(strftime('%m', t.payment_month) AS INTEGER) = 1
     AND CAST(strftime('%Y', t.payment_month) AS INTEGER) = CAST(strftime('%Y', prev.payment_month) AS INTEGER) + 1)
  )
```

---

**Skill `customer_avg_monthly_change`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `avg_monthly_change`, `month_count` |
| source tables | `customer_monthly_diffs` |
| depends_on (builds on) | `customer_monthly_diffs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each customer, compute the average of their month_diff values (average month-to-month change). Also include the count of distinct months to allow filtering customers with fewer than two months._

```sql
SELECT
  cmd.customer_id,
  AVG(cmd.month_diff) AS avg_monthly_change,
  COUNT(DISTINCT cmd.payment_month) AS month_count
FROM
  customer_monthly_diffs AS cmd
GROUP BY
  cmd.customer_id
```

---

**Skill `customer_purchases`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `purchase_ts` |
| output columns | `customer_id`, `purchase_ts`, `amount` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All purchase events with their customer identifier, purchase timestamp, and sale amount. This is the base row-level cohort of every sale record to be used for per-customer lifetime and windowed sums._

```sql
SELECT
  customer_id,
  payment_date AS purchase_ts,
  amount
FROM payment
```

---

**Skill `customer_first_purchase`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `initial_purchase_ts` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_The earliest purchase timestamp per customer (the customer's initial purchase time). One row per customer with their initial purchase time._

```sql
SELECT
  p.customer_id AS customer_id,
  MIN(p.payment_date) AS initial_purchase_ts
FROM payment AS p
GROUP BY p.customer_id
```

---

**Skill `customer_ltv_and_window_sums`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `initial_purchase_ts` |
| output columns | `customer_id`, `ltv_total`, `sum_first_7_days`, `sum_first_30_days`, `initial_purchase_ts` |
| source tables | `customer`, `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_level_percentages_and_averages` |
| validated_on | — |
| counter_examples | 0 |

_For each purchase row, attach the customer's initial purchase timestamp, then aggregate per customer to compute total lifetime sales (LTV), total sales within first 7*24 hours, and total sales within first 30*24 hours relative to the initial purchase timestamp. Do not exclude zero-LTV customers here._

```sql
SELECT
  c.customer_id,
  COALESCE(SUM(p.amount), 0.0) AS ltv_total,
  COALESCE(SUM(CASE WHEN p.payment_date <= datetime(cf.initial_purchase_ts, '+7 days') THEN p.amount END), 0.0) AS sum_first_7_days,
  COALESCE(SUM(CASE WHEN p.payment_date <= datetime(cf.initial_purchase_ts, '+30 days') THEN p.amount END), 0.0) AS sum_first_30_days,
  cf.initial_purchase_ts AS initial_purchase_ts
FROM customer c
LEFT JOIN (
  SELECT customer_id, MIN(payment_date) AS initial_purchase_ts
  FROM payment
  GROUP BY customer_id
) cf ON cf.customer_id = c.customer_id
LEFT JOIN payment p ON p.customer_id = c.customer_id
GROUP BY c.customer_id, cf.initial_purchase_ts
```

---

**Skill `customer_level_percentages_and_averages`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `(single-row) -- one row representing the customer-level averages` |
| output columns | `avg_ltv`, `avg_pct_in_first_7_days`, `avg_pct_in_first_30_days`, `note_on_denominator` |
| source tables | `customer_ltv_and_window_sums` |
| depends_on (builds on) | `customer_ltv_and_window_sums` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From the per-customer aggregates, exclude customers with ltv_total = 0, compute per-customer percentage of LTV earned in first 7 days and first 30 days (as a percentage of that customer's ltv_total), then compute averages across customers: average LTV, average percent in first 7 days, and average percent in first 30 days. Also produce the note_on_denominator confirmation._

```sql
SELECT
  AVG(c.ltv_total) AS avg_ltv,
  AVG(
    CASE
      WHEN c.ltv_total = 0 THEN NULL
      ELSE (CAST(c.sum_first_7_days AS REAL) / CAST(c.ltv_total AS REAL)) * 100.0
    END
  ) AS avg_pct_in_first_7_days,
  AVG(
    CASE
      WHEN c.ltv_total = 0 THEN NULL
      ELSE (CAST(c.sum_first_30_days AS REAL) / CAST(c.ltv_total AS REAL)) * 100.0
    END
  ) AS avg_pct_in_first_30_days,
  'denominator is per-customer ltv_total; customers with ltv_total = 0 excluded from percentage calculations' AS note_on_denominator
FROM customer_ltv_and_window_sums c
WHERE c.ltv_total IS NOT NULL
  AND c.ltv_total != 0
```

---

**Skill `actor_film_credits_sel`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `actor_id`, `film_id`, `credit_id?` |
| output columns | `actor_id`, `film_id`, `credit_id?` |
| source tables | `film_actor`, `film` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Select the cohort of actor-film credit records linking actors to films, restricted to films that have a non-null numeric revenue > 0 and to credits where an actor is recorded. Keep one row per credited actor-film pairing (a single credit record)._

```sql
SELECT
  film_actor.actor_id AS actor_id,
  film_actor.film_id AS film_id,
  film_actor.rowid AS "credit_id?"
FROM film_actor
JOIN film ON film_actor.film_id = film.film_id
WHERE film.release_year IS NOT NULL
  AND film.release_year <> ''
  AND film.replacement_cost IS NOT NULL
  AND CAST(film.replacement_cost AS REAL) > 0
  AND film_actor.actor_id IS NOT NULL
  AND film_actor.film_id IS NOT NULL
```

---

**Skill `film_revenue_and_cast_counts_join`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `actor_id`, `film_id` |
| output columns | `actor_id`, `film_id`, `film_title`, `film_revenue`, `num_credited_actors` |
| source tables | `film_actor`, `film` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `actor_film_share_calc_norm` |
| validated_on | — |
| counter_examples | 1 |

_Attach film-level attributes to each credited actor-film row: the film's title and numeric revenue, and the total number of actors credited in that film (counting all actor credits for the film). Produce one row per credited actor-film with these film attributes included._

```sql
SELECT
  fa.actor_id AS actor_id,
  fa.film_id AS film_id,
  f.title AS film_title,
  (f.replacement_cost * COALESCE(f.length, 1)) AS film_revenue,
  cnt.num_credited_actors AS num_credited_actors
FROM film_actor AS fa
JOIN film AS f ON f.film_id = fa.film_id
JOIN (
  SELECT film_id, COUNT(*) AS num_credited_actors
  FROM film_actor
  GROUP BY film_id
) AS cnt ON cnt.film_id = fa.film_id
```

---

**Skill `actor_film_share_calc_norm`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `actor_id`, `film_id` |
| output columns | `actor_id`, `film_id`, `film_title`, `film_revenue`, `num_credited_actors`, `actor_share_in_film` |
| source tables | `film_revenue_and_cast_counts_join` |
| depends_on (builds on) | `film_revenue_and_cast_counts_join` |
| depended-on by (builds on this) | `top3_per_actor_rank_and_avg` |
| validated_on | — |
| counter_examples | 0 |

_Compute the actor's share in each credited film by dividing the film_revenue equally by num_credited_actors, and project only rows needed for ranking and aggregation. Keep only films where film_revenue > 0 (already enforced) and ensure numeric types are normalized._

```sql
SELECT
  film_revenue_and_cast_counts_join.actor_id AS actor_id,
  film_revenue_and_cast_counts_join.film_id AS film_id,
  film_revenue_and_cast_counts_join.film_title AS film_title,
  CAST(film_revenue_and_cast_counts_join.film_revenue AS NUMERIC) AS film_revenue,
  CAST(film_revenue_and_cast_counts_join.num_credited_actors AS INTEGER) AS num_credited_actors,
  CAST(film_revenue_and_cast_counts_join.film_revenue AS NUMERIC)
    / NULLIF(CAST(film_revenue_and_cast_counts_join.num_credited_actors AS NUMERIC), 0)
    AS actor_share_in_film
FROM film_revenue_and_cast_counts_join
WHERE film_revenue_and_cast_counts_join.film_revenue > 0
```

---

**Skill `top3_per_actor_rank_and_avg`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `actor_id`, `film_id` |
| output columns | `actor_id`, `actor_name?`, `film_id`, `film_title`, `film_revenue`, `num_credited_actors`, `actor_share_in_film`, `rank_within_actor`, `average_share_top3` |
| source tables | `actor_film_share_calc_norm`, `actor`, `film` |
| depends_on (builds on) | `actor_film_share_calc_norm` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each actor, rank their credited films by film_revenue descending (deterministically tie-break by film_id ascending) and keep ranks 1..3. Also compute the actor's average of the actor_share_in_film across the kept top (up to 3) films. Output one row per actor-film kept (up to three rows per actor) including rank and the average share._

```sql
SELECT
  s.actor_id,
  (a.first_name || ' ' || a.last_name) AS "actor_name?",
  s.film_id,
  f.title AS film_title,
  s.film_revenue,
  s.num_credited_actors,
  s.actor_share_in_film,
  -- rank films by film_revenue desc, tie-break film_id asc
  ROW_NUMBER() OVER (
    PARTITION BY s.actor_id
    ORDER BY s.film_revenue DESC, s.film_id ASC
  ) AS rank_within_actor,
  -- average actor_share_in_film over the top 3 ranks per actor
  AVG(s.actor_share_in_film) OVER (
    PARTITION BY s.actor_id
    ORDER BY s.film_revenue DESC, s.film_id ASC
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) * 1.0
    / NULLIF(
        -- compute count of rows from partition start up to current row but cap at 3
        CASE
          WHEN ROW_NUMBER() OVER (
            PARTITION BY s.actor_id
            ORDER BY s.film_revenue DESC, s.film_id ASC
          ) >= 3 THEN 3
          ELSE ROW_NUMBER() OVER (
            PARTITION BY s.actor_id
            ORDER BY s.film_revenue DESC, s.film_id ASC
          )
        END
      , 0) AS average_share_top3
FROM
  actor_film_share_calc_norm AS s
  JOIN actor AS a ON a.actor_id = s.actor_id
  JOIN film AS f ON f.film_id = s.film_id
```

---

**Skill `customer_cohort`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id` |
| source tables | `customer` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All distinct customers to be used as the denominator (no additional filters)._

```sql
SELECT DISTINCT
  customer.customer_id
FROM customer
```

---

**Skill `top_actors_candidates`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `actor_id` |
| output columns | `actor_id`, `actor_rank`, `ranking_metric` |
| source tables | `actor`, `film_actor` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customers_with_top_actor_rentals` |
| validated_on | — |
| counter_examples | 0 |

_Rank actors by the chosen ranking metric (e.g., total film appearances) so the top five can be selected. This produces one row per actor with its rank and metric value._

```sql
SELECT
  a.actor_id AS actor_id,
  RANK() OVER (ORDER BY COUNT(fa.film_id) DESC) AS actor_rank,
  COUNT(fa.film_id) AS ranking_metric
FROM actor a
LEFT JOIN film_actor fa ON fa.actor_id = a.actor_id
GROUP BY a.actor_id
```

---

**Skill `customers_with_top_actor_rentals`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `rental_id` |
| output columns | `customer_id`, `rental_id`, `film_id`, `actor_id` |
| source tables | `rental`, `inventory`, `film_actor`, `top_actors_candidates` |
| depends_on (builds on) | `top_actors_candidates` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All distinct customers who have rented at least one film that features any of the top-five actors (joins rentals to films to the selected top actors). One row per qualifying customer-film-actor rental appearance. Downstream aggregation will deduplicate to one row per customer._

```sql
SELECT
  r.customer_id,
  r.rental_id,
  i.film_id,
  fa.actor_id
FROM
  rental r
JOIN
  inventory i ON r.inventory_id = i.inventory_id
JOIN
  film_actor fa ON i.film_id = fa.film_id
JOIN
  top_actors_candidates tac ON fa.actor_id = tac.actor_id
```

---

**Skill `customer_payments_events`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `payment_id` |
| output columns | `customer_id`, `payment_id`, `payment_date`, `payment_amount`, `movie_id` |
| source tables | `payment`, `rental` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All payment/rental events for customers: one row per payment record including customer id, payment amount, payment date/time, and the rented movie id (or rental id) that the payment corresponds to. Restrict to customers who have at least one payment._

```sql
SELECT
  p.customer_id,
  p.payment_id,
  p.payment_date,
  p.amount AS payment_amount,
  r.inventory_id AS movie_id
FROM payment p
LEFT JOIN rental r
  ON r.rental_id = p.rental_id
WHERE p.customer_id IS NOT NULL
```

---

**Skill `customer_totals_and_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `total_amount_spent`, `total_rental_count` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `first_movie_rating_customer_level` |
| validated_on | — |
| counter_examples | 0 |

_Per-customer aggregates computed from all their payment events: total amount spent (sum of payment_amount) and total number of payments/rentals (count of payment events)._

```sql
SELECT
  p.customer_id AS customer_id,
  SUM(p.amount) AS total_amount_spent,
  COUNT(p.payment_id) AS total_rental_count
FROM payment p
GROUP BY p.customer_id
```

---

**Skill `first_payment_per_customer`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `first_payment_id`, `first_payment_date`, `first_movie_id` |
| source tables | `payment`, `rental`, `inventory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `first_movie_rating_customer_level` |
| validated_on | — |
| counter_examples | 0 |

_Identify the single first payment event per customer by earliest payment_date (tie-broken deterministically if multiple on same datetime) to select that payment's movie_id (the customer's first rented movie)._

```sql
SELECT
  p.customer_id AS customer_id,
  p.payment_id AS first_payment_id,
  p.payment_date AS first_payment_date,
  i.film_id AS first_movie_id
FROM payment p
JOIN rental r ON r.rental_id = p.rental_id
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN (
  SELECT
    customer_id,
    MIN(payment_date) AS min_payment_date,
    MIN(payment_id) AS min_payment_id_tiebreak
  FROM payment
  GROUP BY customer_id
) first_per_cust
  ON p.customer_id = first_per_cust.customer_id
  AND p.payment_date = first_per_cust.min_payment_date
  AND p.payment_id = first_per_cust.min_payment_id_tiebreak
```

---

**Skill `first_movie_rating_customer_level`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `first_movie_rating`, `total_amount_spent`, `total_rental_count`, `subsequent_rentals` |
| source tables | `film` |
| depends_on (builds on) | `first_payment_per_customer`, `customer_totals_and_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Combine each customer's first movie (from first_payment_per_customer) with that movie's rating category, and attach the per-customer totals/counts so each row is one customer with: first_movie_rating, total_amount_spent, total_rental_count. Compute subsequent_rentals = total_rental_count - 1 at the customer row level._

```sql
SELECT
  fpc.customer_id AS customer_id,
  film.rating AS first_movie_rating,
  ctot.total_amount_spent AS total_amount_spent,
  ctot.total_rental_count AS total_rental_count,
  (ctot.total_rental_count - 1) AS subsequent_rentals
FROM
  first_payment_per_customer AS fpc
LEFT JOIN film ON film.film_id = fpc.first_movie_id
LEFT JOIN customer_totals_and_counts AS ctot ON ctot.customer_id = fpc.customer_id
```

---

**Skill `payments_by_customer_month`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month` |
| output columns | `customer_id`, `month`, `payment_amount_in_month` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `consecutive_month_changes_for_top_customers` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate payments into a single payment amount per customer per calendar month. Each row represents the total payment amount that a customer made in that specific month._

```sql
SELECT
  payment.customer_id AS customer_id,
  strftime('%Y-%m', payment.payment_date) AS month,
  SUM(payment.amount) AS payment_amount_in_month
FROM payment
GROUP BY payment.customer_id, strftime('%Y-%m', payment.payment_date)
```

---

**Skill `top_customers_by_total_payments`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `total_payments` |
| source tables | `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute total payments per customer across all time (one row per customer). This relation will be used to identify the top-paying customers._

```sql
SELECT
  payment.customer_id AS customer_id,
  SUM(payment.amount) AS total_payments
FROM payment
GROUP BY payment.customer_id
```

---

**Skill `top_10_customers`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `customer_id`, `rank_by_total_payments` |
| source tables | `customer`, `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Rank customers by their total payments and produce a cohort marking the top customers. This relation should allow selecting the top N customers (N is applied later)._

```sql
SELECT
  c.customer_id,
  RANK() OVER (ORDER BY COALESCE(SUM(p.amount), 0) DESC) AS rank_by_total_payments
FROM customer c
LEFT JOIN payment p ON p.customer_id = c.customer_id
GROUP BY c.customer_id
```

---

**Skill `consecutive_month_changes_for_top_customers`** — category `WIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `month_of_change` |
| output columns | `customer_id`, `month_of_change`, `next_month`, `payment_amount_in_month`, `payment_amount_in_next_month`, `absolute_change` |
| source tables | `payments_by_customer_month` |
| depends_on (builds on) | `payments_by_customer_month` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For payments_by_customer_month restricted to the top customers, pair each customer's month with the immediately following calendar month (only where both months have payments) and compute the absolute change between the month's payment and the next month's payment. Include the earlier month, next month, both amounts, and the absolute change (rounding applied later)._

```sql
SELECT
  t.customer_id AS customer_id,
  t.month AS month_of_change,
  t_next.month AS next_month,
  t.payment_amount_in_month AS payment_amount_in_month,
  t_next.payment_amount_in_month AS payment_amount_in_next_month,
  ABS(t_next.payment_amount_in_month - t.payment_amount_in_month) AS absolute_change
FROM payments_by_customer_month t
JOIN payments_by_customer_month t_next
  ON t.customer_id = t_next.customer_id
  AND (
    (strftime('%Y', t_next.month) = strftime('%Y', t.month) AND (CAST(strftime('%m', t_next.month) AS INTEGER) = CAST(strftime('%m', t.month) AS INTEGER) + 1))
    OR
    (CAST(strftime('%m', t.month) AS INTEGER) = 12 AND CAST(strftime('%m', t_next.month) AS INTEGER) = 1 AND CAST(strftime('%Y', t_next.month) AS INTEGER) = CAST(strftime('%Y', t.month) AS INTEGER) + 1)
  )
```

---

**Skill `staff_created_rentals`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `rental_id` |
| output columns | `rental_id`, `store_id`, `created_timestamp` |
| source tables | `rental`, `staff`, `store` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All rental orders that were created by staff members (exclude rentals not created by staff). Include the rental creation timestamp and the store that the rental belongs to._

```sql
SELECT
  rental.rental_id AS rental_id,
  store.store_id AS store_id,
  rental.rental_date AS created_timestamp
FROM rental
JOIN staff ON rental.staff_id = staff.staff_id
JOIN store ON staff.store_id = store.store_id
```

---

**Skill `rental_year_month`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `rental_id` |
| output columns | `rental_id`, `store_id`, `year`, `month` |
| source tables | `rental`, `inventory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Project year and numeric month extracted from each rental's creation timestamp. Keep one row per rental with its store, year, and month._

```sql
SELECT
  rental.rental_id AS rental_id,
  inventory.store_id AS store_id,
  CAST(strftime('%Y', rental.rental_date) AS INTEGER) AS year,
  CAST(strftime('%m', rental.rental_date) AS INTEGER) AS month
FROM rental
JOIN inventory ON rental.inventory_id = inventory.inventory_id
```

---

**Skill `store_year_month_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `store_id`, `year`, `month` |
| output columns | `store_id`, `year`, `month`, `rental_count` |
| source tables | `rental`, `inventory`, `store` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `store_top_months` |
| validated_on | — |
| counter_examples | 0 |

_Count the number of staff-created rentals grouped by store, year, and month._

```sql
SELECT
  s.store_id AS store_id,
  CAST(strftime('%Y', r.rental_date) AS INTEGER) AS year,
  CAST(strftime('%m', r.rental_date) AS INTEGER) AS month,
  COUNT(r.rental_id) AS rental_count
FROM rental r
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN store s ON i.store_id = s.store_id
GROUP BY s.store_id, year, month
```

---

**Skill `store_top_months`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `store_id`, `year`, `month` |
| output columns | `store_id`, `year`, `month`, `rental_count` |
| source tables | `store_year_month_counts`, `store` |
| depends_on (builds on) | `store_year_month_counts` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For each store, determine the maximum rental_count across year-month groups and keep all year-month rows that tie for that maximum._

```sql
SELECT
  s.store_id,
  sym.year,
  sym.month,
  sym.rental_count
FROM store_year_month_counts AS sym
JOIN store AS s USING (store_id)
WHERE sym.rental_count = (
  SELECT MAX(rental_count)
  FROM store_year_month_counts AS sym2
  WHERE sym2.store_id = sym.store_id
)
```

---
