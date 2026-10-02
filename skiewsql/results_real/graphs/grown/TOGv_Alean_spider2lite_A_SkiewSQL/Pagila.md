# Skill graph — `Pagila` (2 skills)

**Skill `filtered_cast_pairs`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `film_id`, `actor_id` |
| output columns | `film_id`, `actor_id`, `actor_name` |
| source tables | `film`, `actor`, `film_actor` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `actor_appearance_counts` |
| validated_on | — |
| counter_examples | 0 |

_Joins film metadata with cast information to produce a denormalized relation of actor-film associations, restricted to films matching specific language, genre, rating, runtime, and year criteria._

```sql
SELECT film.film_id, actor.actor_id, actor.first_name || ' ' || actor.last_name AS actor_name FROM film JOIN film_actor ON film.film_id = film_actor.film_id JOIN actor ON film_actor.actor_id = actor.actor_id
```

---

**Skill `actor_appearance_counts`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `actor_id`, `actor_name` |
| output columns | `actor_id`, `actor_name`, `film_count` |
| source tables | `filtered_cast_pairs` |
| depends_on (builds on) | `filtered_cast_pairs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Groups the filtered actor-film associations by actor to calculate the total number of qualifying films each actor has starred in._

```sql
SELECT actor_id, actor_name, COUNT(film_id) AS film_count
FROM filtered_cast_pairs
GROUP BY actor_id, actor_name
```

---
