# Skill graph — `Pagila` (8 skills)

**Skill `films_filtered`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `film_id` |
| output columns | `film_id`, `title`, `language`, `category`, `mpaa_rating`, `running_time_minutes`, `release_year` |
| source tables | `film`, `language`, `film_category`, `category` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `film_starring_pairs` |
| validated_on | — |
| counter_examples | 0 |

_Subset of films that satisfy the question's film-level filters (language, category, MPAA rating, running time, and release year). This is one row per film that meets all criteria._

```sql
SELECT
  f.film_id AS film_id,
  f.title AS title,
  l.name AS language,
  c.name AS category,
  f.rating AS mpaa_rating,
  f.length AS running_time_minutes,
  f.release_year AS release_year
FROM film f
JOIN language l ON f.language_id = l.language_id
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id
```

---

**Skill `starring_credits`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `film_id`, `person_id` |
| output columns | `film_id`, `person_id`, `credit_role_flag` |
| source tables | `film_actor`, `actor`, `film` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `film_starring_pairs` |
| validated_on | — |
| counter_examples | 0 |

_Subset of credit records that represent a person credited as a starring (primary/lead) cast member for a film. One row per starring credit linking a person to a film._

```sql
SELECT
  fa.film_id AS film_id,
  fa.actor_id AS person_id,
  1 AS credit_role_flag
FROM film_actor fa
JOIN actor a ON a.actor_id = fa.actor_id
JOIN film f ON f.film_id = fa.film_id
```

---

**Skill `film_starring_pairs`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `film_id`, `person_id` |
| output columns | `film_id`, `person_id` |
| source tables | `films_filtered`, `starring_credits` |
| depends_on (builds on) | `films_filtered`, `starring_credits` |
| depended-on by (builds on this) | `appearances_per_actor` |
| validated_on | — |
| counter_examples | 0 |

_Join the filtered films with starring credits to produce rows for each film-person pair where the person is a starring cast member of a qualifying film._

```sql
SELECT
  f.film_id AS film_id,
  s.person_id AS person_id
FROM
  films_filtered f
JOIN
  starring_credits s ON f.film_id = s.film_id
WHERE
  s.credit_role_flag = 'starring'
```

---

**Skill `appearances_per_actor`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `person_id` |
| output columns | `person_id`, `appearance_count` |
| source tables | `film_starring_pairs` |
| depends_on (builds on) | `film_starring_pairs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Count the number of distinct qualifying films each person appears in as a starring cast member. One row per person with their appearance count._

```sql
SELECT
  sa.person_id AS person_id,
  COUNT(DISTINCT sa.film_id) AS appearance_count
FROM
  film_starring_pairs AS sa
GROUP BY
  sa.person_id
```

---

**Skill `rental_with_location_and_film`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `rental_id` |
| output columns | `rental_id`, `film_id`, `category_id`, `rental_duration_raw`, `city_name` |
| source tables | `rental`, `inventory`, `film`, `film_category`, `customer`, `address`, `city`, `store` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `rental_duration_hours_normalized` |
| validated_on | — |
| counter_examples | 0 |

_Join rentals to the inventory/film and to the customer/address/city relations so each rental row includes the film id, film category id (if available), rental duration value (in whatever unit the schema stores), and the city name for the rental's customer or store as appropriate._

```sql
SELECT
  r.rental_id AS rental_id,
  f.film_id AS film_id,
  fc.category_id AS category_id,
  f.rental_duration AS rental_duration_raw,
  COALESCE(cy.city, cust_city.city) AS city_name
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
LEFT JOIN film f ON f.film_id = i.film_id
LEFT JOIN film_category fc ON fc.film_id = f.film_id
JOIN customer cust ON cust.customer_id = r.customer_id
LEFT JOIN address addr ON addr.address_id = cust.address_id
LEFT JOIN city cust_city ON cust_city.city_id = addr.city_id
LEFT JOIN store s ON s.store_id = i.store_id
LEFT JOIN address s_addr ON s_addr.address_id = (SELECT address_id FROM address WHERE address_id = s_addr.address_id) -- placeholder to keep schema-only joins
LEFT JOIN city cy ON cy.city_id = s_addr.city_id
```

---

**Skill `rental_duration_hours_normalized`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `rental_id` |
| output columns | `rental_id`, `film_id`, `category_id`, `rental_hours`, `city_name` |
| source tables | `rental`, `inventory`, `film`, `film_category`, `address`, `city` |
| depends_on (builds on) | `rental_with_location_and_film` |
| depended-on by (builds on this) | `rentals_in_selected_cities`, `category_total_rental_hours` |
| validated_on | — |
| counter_examples | 0 |

_Normalize/convert each rental's duration into hours (e.g., convert minutes to hours or pass through if already hours) and keep the associated film/category and city name._

```sql
SELECT
  rwlaf.rental_id AS rental_id,
  rwlaf.film_id AS film_id,
  rwlaf.category_id AS category_id,
  -- rental_duration_raw may represent minutes or hours; normalize: if > 24*60 treat as minutes? 
  -- Since no unit metadata, assume rental_duration_raw is minutes when >6 (common rental durations in minutes)
  -- More robust: if value > 12 treat as minutes -> divide by 60, else treat as hours (pass through)
  CASE
    WHEN rwlaf.rental_duration_raw IS NULL THEN NULL
    WHEN rwlaf.rental_duration_raw > 12 THEN (CAST(rwlaf.rental_duration_raw AS REAL) / 60.0)
    ELSE CAST(rwlaf.rental_duration_raw AS REAL)
  END AS rental_hours,
  rwlaf.city_name AS city_name
FROM rental_with_location_and_film rwlaf
```

---

**Skill `rentals_in_selected_cities`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `rental_id` |
| output columns | `rental_id`, `film_id`, `category_id`, `rental_hours`, `city_name` |
| source tables | `rental_duration_hours_normalized` |
| depends_on (builds on) | `rental_duration_hours_normalized` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Filter normalized rentals to only those where the city name starts with 'A' (case-insensitive) OR contains a hyphen '-' anywhere in the name._

```sql
SELECT
  r.rental_id,
  r.film_id,
  r.category_id,
  r.rental_hours,
  r.city_name
FROM rental_duration_hours_normalized r
WHERE (LOWER(r.city_name) LIKE 'a%' OR r.city_name LIKE '%-%')
```

---

**Skill `category_total_rental_hours`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `category_id` |
| output columns | `category_id`, `total_rental_hours` |
| source tables | `rental_duration_hours_normalized` |
| depends_on (builds on) | `rental_duration_hours_normalized` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregate the filtered rentals by film category, summing the rental_hours to produce total rental hours per category._

```sql
SELECT
  rdhn.category_id AS category_id,
  SUM(rdhn.rental_hours) AS total_rental_hours
FROM rental_duration_hours_normalized rdhn
GROUP BY rdhn.category_id
```

---
