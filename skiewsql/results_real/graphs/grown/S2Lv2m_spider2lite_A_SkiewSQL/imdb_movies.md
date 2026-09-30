# Skill graph — `imdb_movies` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `director_mapping`, `movies`, `ratings`, `names` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 1 |

_Task: Compute the top 9 directors ranked by how many movies they directed, returning for each director their ID, name, number of movies, average inter-movie duration (rounded to the nearest integer), _

```sql
SELECT
  dm.name_id AS director_id,
  n.name AS director_name,
  m_counts.movie_count,
  m_counts.avg_inter_movie_duration,
  r_stats.avg_rating,
  r_stats.total_votes,
  r_stats.min_rating,
  r_stats.max_rating,
  m_counts.total_duration
FROM director_mapping dm
LEFT JOIN (
  SELECT
    movie_id,
    movie_id AS movie_id_passthrough
  FROM director_mapping
) dm_passthrough ON dm.movie_id = dm_passthrough.movie_id_passthrough
LEFT JOIN (
  SELECT
    d.name_id,
    COUNT(DISTINCT d.movie_id) AS movie_count,
    -- average inter-movie duration placeholder computed from movie years and dates where available:
    -- compute per-director: for directors with >=2 movies, average of differences in years between consecutive movies (rounded to nearest integer);
    -- This chunk has movies.year and movies.date_published and duration; include both for downstream use.
    ROUND(
      AVG(
        -- compute difference in days between consecutive date_published values if available, otherwise use difference in years*365
        COALESCE(
          (julianday(next_date) - julianday(curr_date)),
          (next_year - curr_year) * 365.0
        )
      )
    ) AS avg_inter_movie_duration,
    SUM(m.duration) AS total_duration
  FROM director_mapping d
  JOIN movies m ON d.movie_id = m.id
  LEFT JOIN (
    -- prepare ordering by date_published and year per director to allow calculating next/previous movie gaps in downstream steps
    SELECT
      d2.name_id,
      d2.movie_id,
      m2.date_published AS curr_date,
      m2.year AS curr_year,
      LEAD(m2.date_published) OVER (PARTITION BY d2.name_id ORDER BY m2.date_published, m2.year) AS next_date,
      LEAD(m2.year) OVER (PARTITION BY d2.name_id ORDER BY m2.date_published, m2.year) AS next_year
    FROM director_mapping d2
    JOIN movies m2 ON d2.movie_id = m2.id
  ) gaps ON gaps.name_id = d.name_id AND gaps.movie_id = d.movie_id
  GROUP BY d.name_id
) m_counts ON m_counts.name_id = dm.name_id
LEFT JOIN (
  SELECT
    r.movie_id,
    r.avg_rating,
    r.total_votes,
    r.median_rating
  FROM ratings r
) r ON r.movie_id = dm.movie_id
LEFT JOIN (
  SELECT
    d.name_id,
    AVG(r2.avg_rating) AS avg_rating,
    SUM(r2.total_votes) AS total_votes,
    MIN(r2.avg_rating) AS min_rating,
    MAX(r2.avg_rating) AS max_rating
  FROM director_mapping d
  JOIN ratings r2 ON d.movie_id = r2.movie_id
  GROUP BY d.name_id
) r_stats ON r_stats.name_id = dm.name_id
LEFT JOIN names n ON n.id = dm.name_id
```

---
