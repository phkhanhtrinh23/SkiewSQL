# Skill graph — `imdb_movies` (2 skills)

**Skill `director_movies_ordered`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `director_id`, `movie_id` |
| output columns | `director_id`, `director_name`, `movie_id`, `release_date`, `movie_duration`, `rating`, `vote_count` |
| source tables | `director_mapping`, `names`, `movies`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `director_aggregates` |
| validated_on | — |
| counter_examples | 0 |

_combines director information with their directed movies, selecting director identifiers, release dates, durations, ratings, and vote counts to establish a chronological record per director_

```sql
SELECT dm.name_id AS director_id, n.name AS director_name, dm.movie_id AS movie_id, m.date_published AS release_date, m.duration AS movie_duration, r.avg_rating AS rating, r.total_votes AS vote_count FROM director_mapping dm JOIN names n ON dm.name_id = n.id JOIN movies m ON dm.movie_id = m.id JOIN ratings r ON m.id = r.movie_id
```

---

**Skill `director_aggregates`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `director_id`, `director_name` |
| output columns | `director_id`, `director_name`, `movie_count`, `avg_inter_movie_duration`, `avg_rating`, `total_votes`, `min_rating`, `max_rating`, `total_movie_duration` |
| source tables | `director_movies_ordered` |
| depends_on (builds on) | `director_movies_ordered` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_computes per-director summary statistics including movie count, total votes, rating statistics, total duration, and average inter-movie duration derived from the chronological movie records_

```sql
SELECT
    director_id,
    director_name,
    COUNT(movie_id) AS movie_count,
    AVG(diff) AS avg_inter_movie_duration,
    AVG(rating) AS avg_rating,
    SUM(vote_count) AS total_votes,
    MIN(rating) AS min_rating,
    MAX(rating) AS max_rating,
    SUM(movie_duration) AS total_movie_duration
FROM (
    SELECT
        director_id,
        director_name,
        movie_id,
        rating,
        vote_count,
        movie_duration,
        movie_duration - LAG(movie_duration) OVER (PARTITION BY director_id ORDER BY release_date) AS diff
    FROM director_movies_ordered
)
GROUP BY director_id, director_name
```

---
