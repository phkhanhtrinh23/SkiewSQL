# Skill graph — `Pagila` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `film_actor`, `actor`, `film`, `film_category`, `language` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Identify the single actor who appears as a performer in the largest number of films that meet all specified criteria.
Required outputs: actor full name (string); count of qualifying films the ac_

```sql
SELECT
  a.actor_id,
  a.first_name,
  a.last_name,
  fa.film_id,
  f.language_id,
  f.rating,
  f.length,
  f.release_year,
  fc.category_id
FROM film_actor fa
JOIN actor a ON fa.actor_id = a.actor_id
JOIN film f ON fa.film_id = f.film_id
JOIN film_category fc ON f.film_id = fc.film_id
JOIN language l ON f.language_id = l.language_id
WHERE l.name = 'English'
  AND fc.category_id IS NOT NULL
  AND f.rating IN ('G', 'PG')
  AND f.length <= 120
  AND f.release_year BETWEEN '2000' AND '2010'
```

---
