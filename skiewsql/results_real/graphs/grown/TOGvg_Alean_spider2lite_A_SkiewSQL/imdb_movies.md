# Skill graph — `imdb_movies` (2 skills)

**Skill `director_movie_links`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `director_id`, `movie_id` |
| output columns | `director_id`, `director_name`, `movie_duration`, `rating`, `votes`, `release_date` |
| source tables | `director_mapping`, `names`, `movies`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `director_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_links each director to their directed movies, providing director identifiers, movie duration, rating, vote count, and release date for temporal ordering_

```sql
SELECT dm.name_id AS director_id, n.name AS director_name, m.duration AS movie_duration, r.avg_rating AS rating, r.total_votes AS votes, m.date_published AS release_date FROM director_mapping dm JOIN names n ON dm.name_id = n.id JOIN movies m ON dm.movie_id = m.id JOIN ratings r ON dm.movie_id = r.movie_id
```

---

**Skill `director_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `director_id`, `director_name` |
| output columns | `director_id`, `director_name`, `movie_count`, `avg_inter_movie_duration`, `avg_rating`, `total_votes`, `min_rating`, `max_rating`, `total_movie_duration` |
| source tables | `director_movie_links` |
| depends_on (builds on) | `director_movie_links` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_computes per-director statistics including movie count, rating metrics, vote totals, duration sums, and average inter-movie duration derived from ordered release dates_

```sql
SELECT
  director_id,
  director_name,
  COUNT(*) AS movie_count,
  AVG(diff_days) AS avg_inter_movie_duration,
  AVG(rating) AS avg_rating,
  SUM(votes) AS total_votes,
  MIN(rating) AS min_rating,
  MAX(rating) AS max_rating,
  SUM(movie_duration) AS total_movie_duration
FROM (
  SELECT
    director_id,
    director_name,
    movie_duration,
    rating,
    votes,
    release_date,
    CAST(julianday(release_date) - julianday(LAG(release_date) OVER (PARTITION BY director_id ORDER BY release_date)) AS INTEGER) AS diff_days
  FROM director_movie_links
)
GROUP BY director_id, director_name
```

---
