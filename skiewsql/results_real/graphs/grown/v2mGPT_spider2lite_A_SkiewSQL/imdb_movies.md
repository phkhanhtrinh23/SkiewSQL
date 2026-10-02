# Skill graph — `imdb_movies` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `director_mapping`, `names`, `movies`, `ratings` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Compute the top 9 directors ranked by how many movies they directed, and for each director produce their id, name, number of movies, average inter-movie duration (rounded to nearest integer), av_

```sql
SELECT
  d.name_id AS director_id,
  n.name AS director_name,
  m.id AS movie_id,
  m.date_published,
  m.duration,
  r.avg_rating,
  r.total_votes
FROM director_mapping d
LEFT JOIN names n ON d.name_id = n.id
LEFT JOIN movies m ON d.movie_id = m.id
LEFT JOIN ratings r ON m.id = r.movie_id
```

---
