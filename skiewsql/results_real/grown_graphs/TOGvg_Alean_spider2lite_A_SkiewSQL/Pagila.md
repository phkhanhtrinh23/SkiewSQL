# Skill graph — `Pagila` (2 skills)

**Skill `qualified_film_actor_links`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `film`, `actor` |
| output columns | `film`, `actor`, `actor_full_name` |
| source tables | `film_actor`, `film`, `actor` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `actor_starring_counts` |
| validated_on | — |
| counter_examples | 0 |

_Links each actor to the films they starred in, applying all specified criteria to the film cohort._

```sql
SELECT fa.film_id AS film, fa.actor_id AS actor, a.first_name || ' ' || a.last_name AS actor_full_name
FROM film_actor fa
JOIN film f ON fa.film_id = f.film_id
JOIN actor a ON fa.actor_id = a.actor_id
```

---

**Skill `actor_starring_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `actor`, `actor_full_name` |
| output columns | `actor`, `actor_full_name`, `film_count` |
| source tables | `qualified_film_actor_links` |
| depends_on (builds on) | `qualified_film_actor_links` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregates the linked film-actor pairs to count the number of qualifying films each actor appeared in._

```sql
SELECT actor, actor_full_name, COUNT(film) AS film_count
FROM qualified_film_actor_links
GROUP BY actor, actor_full_name
```

---
