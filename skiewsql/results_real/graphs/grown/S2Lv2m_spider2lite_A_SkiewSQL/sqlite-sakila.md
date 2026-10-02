# Skill graph — `sqlite-sakila` (5 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `payment`, `customer` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | Among our top 10 paying customers, can you identify the largest change in payment amounts from one month to the immediately following month? Specifically, please determine for which customer and during which month this maximum month-over-month difference occurred, and provide the difference rounded  |
| counter_examples | 0 |

_Task: Find the customer whose average monthly change in payment amounts is the largest (most positive), and return that customer's full name. Required outputs: customer full name (first name and last _

```sql
SELECT
  p.customer_id,
  c.first_name,
  c.last_name,
  p.payment_date,
  p.amount
FROM payment p
JOIN customer c ON p.customer_id = c.customer_id
```

---

**Skill `chunk_view_0_1`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customer`, `payment`, `rental`, `inventory` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the average share of each customer's total lifetime sales (LTV) that occurred within the first 7 days (168 hours) and within the first 30 days (720 hours) after that customer's first-eve_

```sql
SELECT
  c.customer_id,
  p.payment_id,
  p.amount,
  p.payment_date,
  r.rental_id,
  r.rental_date,
  inv.inventory_id,
  inv.film_id,
  c.create_date AS customer_create_date
FROM customer c
LEFT JOIN payment p ON p.customer_id = c.customer_id
LEFT JOIN rental r ON r.rental_id = p.rental_id
LEFT JOIN inventory inv ON inv.inventory_id = r.inventory_id
```

---

**Skill `chunk_view_0_2`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `actor`, `film_actor`, `film`, `inventory`, `rental`, `payment` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | Please find out how widespread the appeal of our top five actors is. What percentage of our customers have rented films featuring these actors? |
| counter_examples | 0 |

_Task: For each actor, find their top three films by that film's total revenue, and for each of those films compute the actor's share of the film's revenue by dividing the film's total revenue equally _

```sql
SELECT
  actor.actor_id,
  actor.first_name,
  actor.last_name,
  film.film_id,
  film.title,
  -- revenue is not stored in this chunk; include any columns needed to join later (e.g., rental/payment/inventory)
  rental.rental_id,
  rental.rental_date,
  rental.return_date,
  payment.payment_id,
  payment.amount,
  inventory.inventory_id,
  film_actor.last_update        AS film_actor_last_update,
  film.last_update              AS film_last_update
FROM actor
JOIN film_actor ON film_actor.actor_id = actor.actor_id
JOIN film ON film.film_id = film_actor.film_id
LEFT JOIN inventory ON inventory.film_id = film.film_id
LEFT JOIN rental ON rental.inventory_id = inventory.inventory_id
LEFT JOIN payment ON payment.rental_id = rental.rental_id
```

---

**Skill `chunk_view_0_3`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `customer`, `payment`, `rental`, `inventory`, `film` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each movie rating category that is the rating of a customer's earliest-paid rental (earliest payment date per customer), compute the average total amount spent per such customer and the aver_

```sql
SELECT
  customer.customer_id,
  payment.payment_id,
  payment.payment_date,
  rental.rental_id,
  rental.inventory_id,
  inventory.film_id,
  film.rating,
  payment.amount,
  -- include all payments per customer will be aggregated later; keep payment rows
  customer.create_date,
  customer.store_id
FROM customer
JOIN payment ON payment.customer_id = customer.customer_id
JOIN rental ON rental.rental_id = payment.rental_id
JOIN inventory ON inventory.inventory_id = rental.inventory_id
JOIN film ON film.film_id = inventory.film_id
```

---

**Skill `chunk_view_0_4`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `rental`, `staff`, `store` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each store, find the year and month in which the highest number of rental orders were created by that store's staff, and report the store ID, that year, that month, and the total number of r_

```sql
SELECT
    s.store_id,
    r.rental_id,
    r.rental_date,
    r.customer_id,
    r.inventory_id,
    r.staff_id,
    st.store_id AS staff_store_id,
    st.staff_id
FROM rental r
JOIN staff st ON r.staff_id = st.staff_id
JOIN store s ON st.store_id = s.store_id
```

---
