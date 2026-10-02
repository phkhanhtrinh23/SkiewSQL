# Skill graph — `Db-IMDB` (2 skills)

**Skill `movie_actor_year`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `movie_id`, `actor_id` |
| output columns | `movie_id`, `actor_id`, `year`, `actor_gender` |
| source tables | `Movie`, `M_Cast`, `Person` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `year_movie_stats` |
| validated_on | — |
| counter_examples | 0 |

_links each movie to its cast members and extracts the release year from the movie record_

```sql
SELECT Movie.MID AS movie_id, Person.PID AS actor_id, Movie.year AS year, Person.Gender AS actor_gender FROM Movie JOIN M_Cast ON Movie.MID = M_Cast.MID JOIN Person ON M_Cast.PID = Person.PID
```

---

**Skill `year_movie_stats`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `year` |
| output columns | `year`, `total_movies`, `percentage_exclusively_female_actors` |
| source tables | `movie_actor_year` |
| depends_on (builds on) | `movie_actor_year` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_evaluates per movie whether all cast members meet the gender condition, then groups by year to compute total movie count and the percentage of movies satisfying the condition_

```sql
SELECT
    year,
    COUNT(DISTINCT movie_id) AS total_movies,
    CAST(COUNT(CASE WHEN NOT EXISTS (
        SELECT 1 FROM movie_actor_year m2
        WHERE m2.movie_id = m1.movie_id AND m2.actor_gender != 'Female'
    ) THEN 1 ELSE 0 END) AS REAL) * 100.0 / COUNT(DISTINCT movie_id) AS percentage_exclusively_female_actors
FROM movie_actor_year m1
GROUP BY year
```

---
