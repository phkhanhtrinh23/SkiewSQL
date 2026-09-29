# Skill graph — `imdb_movies` (8 skills)

**Skill `director_movie_links`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `director_id`, `movie_id` |
| output columns | `director_id`, `director_name`, `movie_id`, `movie_duration`, `movie_rating`, `movie_votes`, `movie_release_date` |
| source tables | `director_mapping`, `names`, `movies`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `director_final_metrics` |
| validated_on | — |
| counter_examples | 0 |

_One-row-per association of a director with a single movie, including the movie's primary metrics needed for aggregation (duration, rating, votes, release date). This denormalizes director-to-movie relationships so each row is a director-movie pair._

```sql
SELECT
  director_mapping.name_id AS director_id,
  names.name AS director_name,
  director_mapping.movie_id AS movie_id,
  movies.duration AS movie_duration,
  ratings.avg_rating AS movie_rating,
  ratings.total_votes AS movie_votes,
  movies.date_published AS movie_release_date
FROM director_mapping
LEFT JOIN names ON director_mapping.name_id = names.id
LEFT JOIN movies ON director_mapping.movie_id = movies.id
LEFT JOIN ratings ON director_mapping.movie_id = ratings.movie_id
```

---

**Skill `director_movie_stats_per_movie`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `director_id`, `movie_id` |
| output columns | `director_id`, `director_name`, `movie_id`, `movie_duration`, `movie_rating`, `movie_votes`, `movie_release_timestamp` |
| source tables | `director_mapping`, `names`, `movies`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Normalize/clean per director-movie rows: ensure numeric types for duration, rating, votes and canonical director name (handle nulls), and compute any per-movie derived fields needed for later aggregation (e.g., release timestamp for inter-movie interval computation). Still one row per director-movie._

```sql
SELECT
  dm.name_id AS director_id,
  COALESCE(n.name, '') AS director_name,
  dm.movie_id AS movie_id,
  CAST(m.duration AS INTEGER) AS movie_duration,
  CAST(r.avg_rating AS REAL) AS movie_rating,
  CAST(r.total_votes AS INTEGER) AS movie_votes,
  CAST(strftime('%s', m.date_published) AS INTEGER) AS movie_release_timestamp
FROM director_mapping dm
LEFT JOIN names n ON n.id = dm.name_id
LEFT JOIN movies m ON m.id = dm.movie_id
LEFT JOIN ratings r ON r.movie_id = dm.movie_id
```

---

**Skill `director_intervals`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name_id` |
| output columns | `director_id`, `movie_count`, `min_release_timestamp`, `max_release_timestamp`, `sum_movie_durations`, `sum_movie_votes`, `avg_movie_rating`, `min_movie_rating`, `max_movie_rating` |
| source tables | `director_mapping`, `movies`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `director_final_metrics` |
| validated_on | — |
| counter_examples | 0 |

_Per director, compute ordered list/aggregate measures needed to derive average inter-movie duration: produce count of movies and the sequence boundaries (min and max release timestamps) and optionally average gap using release timestamps; also include sums, min, max of ratings, total votes, and total duration per director. This yields per-director aggregated measures but preserves movie_count as a key._

```sql
SELECT
  dm.name_id AS director_id,
  COUNT(DISTINCT m.id) AS movie_count,
  MIN(m.date_published) AS min_release_timestamp,
  MAX(m.date_published) AS max_release_timestamp,
  SUM(m.duration) AS sum_movie_durations,
  SUM(r.total_votes) AS sum_movie_votes,
  AVG(r.avg_rating) AS avg_movie_rating,
  MIN(r.avg_rating) AS min_movie_rating,
  MAX(r.avg_rating) AS max_movie_rating
FROM director_mapping dm
JOIN movies m ON dm.movie_id = m.id
LEFT JOIN ratings r ON m.id = r.movie_id
GROUP BY dm.name_id
```

---

**Skill `director_final_metrics`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `director_id` |
| output columns | `director_id`, `director_name`, `movie_count`, `avg_inter_movie_duration`, `avg_rating`, `total_votes`, `min_rating`, `max_rating`, `total_movie_duration` |
| source tables | `director_intervals`, `director_movie_links` |
| depends_on (builds on) | `director_movie_links`, `director_intervals` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Combine per-director aggregates to compute final metrics: average inter-movie duration (derived from min/max and movie_count), rounded values for required fields, and apply sorting and top-k selection (ordering by movie_count desc then total duration desc). This returns one row per director ready for the top-9 selection._

```sql
SELECT
  d.director_id AS director_id,
  d.director_name AS director_name,
  i.movie_count AS movie_count,
  CASE
    WHEN i.movie_count <= 1 THEN NULL
    ELSE ROUND(( (i.max_release_timestamp - i.min_release_timestamp) / (i.movie_count - 1) ) , 2)
  END AS avg_inter_movie_duration,
  ROUND(i.avg_movie_rating, 2) AS avg_rating,
  i.sum_movie_votes AS total_votes,
  i.min_movie_rating AS min_rating,
  i.max_movie_rating AS max_rating,
  i.sum_movie_durations AS total_movie_duration
FROM director_intervals i
JOIN (
  SELECT DISTINCT director_id, director_name
  FROM director_movie_links
) d USING (director_id)
```

---

**Skill `high_rated_movies`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `movie_id` |
| output columns | `movie_id`, `title`, `rating`, `genre_id`, `director_id` |
| source tables | `movies`, `ratings`, `genre`, `director_mapping` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All movies that satisfy the rating filter (rating > 8), with their identifying info and links to genre and director._

```sql
SELECT
  m.id AS movie_id,
  m.title AS title,
  r.avg_rating AS rating,
  g.genre AS genre_id,
  dm.name_id AS director_id
FROM movies m
JOIN ratings r ON r.movie_id = m.id
LEFT JOIN genre g ON g.movie_id = m.id
LEFT JOIN director_mapping dm ON dm.movie_id = m.id
WHERE r.avg_rating > 8
```

---

**Skill `movies_by_genre`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `genre` |
| output columns | `genre_id`, `genre_movie_count` |
| source tables | `genre`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Count of high-rated movies per genre (one row per genre)._

```sql
SELECT
  g.genre AS genre_id,
  COUNT(DISTINCT g.movie_id) AS genre_movie_count
FROM genre g
JOIN ratings r ON r.movie_id = g.movie_id
WHERE r.avg_rating >= 8.0
GROUP BY g.genre
```

---

**Skill `movies_by_genre_director`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `genre`, `name_id` |
| output columns | `genre_id`, `director_id`, `director_movie_count` |
| source tables | `genre`, `director_mapping` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Count of high-rated movies per (genre, director) pair (one row per genre and director)._

```sql
SELECT
  g.genre AS genre_id,
  dm.name_id AS director_id,
  COUNT(*) AS director_movie_count
FROM genre g
JOIN director_mapping dm
  ON g.movie_id = dm.movie_id
GROUP BY
  g.genre,
  dm.name_id
```

---

**Skill `top_genres_and_directors`** — category `RANK`

| field | value |
|---|---|
| grain (one row per) | `genre_id`, `director_id` |
| output columns | `genre_id`, `director_id`, `genre_movie_count`, `director_movie_count` |
| source tables | `genre`, `director_mapping` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_From genre-level counts, pick the top 3 genres by genre_movie_count, and within those genres pick the top 4 directors by director_movie_count; produce rows with genre, director, and counts ready for final output._

```sql
SELECT
  g.genre AS genre_id,
  d.name_id AS director_id,
  genre_counts.genre_movie_count AS genre_movie_count,
  COALESCE(dm.director_movie_count, 0) AS director_movie_count
FROM
  (
    SELECT
      genre,
      COUNT(DISTINCT movie_id) AS genre_movie_count
    FROM genre
    GROUP BY genre
  ) AS genre_counts
JOIN genre g ON g.genre = genre_counts.genre
LEFT JOIN (
  SELECT
    genre AS genre,
    name_id,
    COUNT(DISTINCT movie_id) AS director_movie_count
  FROM genre
  JOIN director_mapping USING(movie_id)
  GROUP BY genre, name_id
) AS dm ON dm.genre = genre_counts.genre
JOIN director_mapping d ON d.movie_id IN (
  SELECT movie_id FROM genre WHERE genre = genre_counts.genre
) AND d.name_id = dm.name_id
WHERE genre_counts.genre IN (
  SELECT genre FROM (
    SELECT genre, COUNT(DISTINCT movie_id) AS cnt
    FROM genre
    GROUP BY genre
    ORDER BY cnt DESC
    LIMIT 3
  )
)
AND dm.name_id IN (
  SELECT name_id FROM (
    SELECT name_id, COUNT(DISTINCT movie_id) AS cnt
    FROM director_mapping
    JOIN genre USING(movie_id)
    WHERE genre = genre_counts.genre
    GROUP BY name_id
    ORDER BY cnt DESC
    LIMIT 4
  )
)
```

---
