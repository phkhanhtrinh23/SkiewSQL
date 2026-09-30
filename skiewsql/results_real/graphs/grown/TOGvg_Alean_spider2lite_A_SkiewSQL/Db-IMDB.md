# Skill graph — `Db-IMDB` (2 skills)

**Skill `movie_actor_year`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `movie_id`, `actor_id`, `year` |
| output columns | `movie_id`, `actor_id`, `year`, `actor_gender` |
| source tables | `Movie`, `M_Cast`, `Person` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Denormalized relation linking each movie to its associated actors, including the extracted year and actor gender._

```sql
SELECT m.MID AS movie_id, p.PID AS actor_id, m.year AS year, p.Gender AS actor_gender FROM Movie m JOIN M_Cast c ON m.MID = c.MID JOIN Person p ON c.PID = p.PID
```

---

**Skill `year_movie_metrics`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `total_movies`, `percentage_exclusively_female_actors` |
| source tables | `Movie`, `M_Cast`, `Person` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregates per year to compute total movies and the percentage of movies that qualify as exclusively female based on associated actor genders._

```sql
SELECT
    m.year,
    COUNT(DISTINCT m.MID) AS total_movies,
    100.0 * COUNT(DISTINCT m_exf.MID) / COUNT(DISTINCT m.MID) AS percentage_exclusively_female_actors
FROM Movie m
LEFT JOIN (
    SELECT mc.MID
    FROM M_Cast mc
    JOIN Person p ON mc.PID = p.PID
    GROUP BY mc.MID
    HAVING MIN(p.Gender) = 'Female' AND MAX(p.Gender) = 'Female'
) m_exf ON m.MID = m_exf.MID
GROUP BY m.year
```

---
