# Skill graph — `Db-IMDB` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `Movie`, `M_Cast`, `Person` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: For each year (obtained by taking the last 4 characters of Movie.year and converting them to a number), compute the total number of movies released that year and the percentage of those movies w_

```sql
SELECT
  Movie.MID,
  Movie.year,
  -- extracted year as text (last 4 chars); conversion to numeric will be done later
  substr(Movie.year, -4, 4) AS year_text,
  Movie."index" AS movie_index,
  -- cast member link
  M_Cast.PID AS cast_PID,
  -- person info for each cast member
  Person.Name AS person_name,
  Person.Gender AS person_gender
FROM Movie
LEFT JOIN M_Cast ON M_Cast.MID = Movie.MID
LEFT JOIN Person ON Person.PID = M_Cast.PID
WHERE length(substr(Movie.year, -4, 4)) = 4
  AND substr(Movie.year, -4, 4) GLOB '[0-9][0-9][0-9][0-9]'
```

---
