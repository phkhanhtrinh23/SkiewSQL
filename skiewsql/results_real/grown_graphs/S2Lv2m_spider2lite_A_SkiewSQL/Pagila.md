# Skill graph — `Pagila` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `film_actor`, `actor`, `film`, `film_category`, `category` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the single actor (full name) who appears as a cast member most often in films that meet all specified constraints.
Required outputs: actor_full_name (the actor's full name as a single strin_

```sql
SELECT
  fa.actor_id,
  a.first_name,
  a.last_name,
  f.film_id,
  f.title,
  f.language_id,
  f.rating,
  f.length,
  f.release_year,
  fc.category_id,
  c.name AS category_name
FROM film_actor fa
JOIN actor a ON fa.actor_id = a.actor_id
JOIN film f ON fa.film_id = f.film_id
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id
WHERE f.language_id IS NOT NULL
  AND f.rating IS NOT NULL
  AND f.length IS NOT NULL
  AND f.release_year IS NOT NULL
  AND c.name IS NOT NULL
```

---
