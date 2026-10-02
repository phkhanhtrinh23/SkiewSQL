# Skill graph — `Baseball` (4 skills)

**Skill `player_debut_final`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `player_id`, `debut_date`, `final_date` |
| source tables | `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `date_diff_years` |
| validated_on | — |
| counter_examples | 0 |

_Selects player debut and final game dates._

```sql
SELECT
    p."player_id" AS player_id,
    p."debut" AS debut_date,
    p."final_game" AS final_date
FROM "player" AS p
```

---

**Skill `date_diff_years`** — category `NORM`

| field | value |
|---|---|
| grain (one row per) | `player_id` |
| output columns | `years` |
| source tables | `player_debut_final` |
| depends_on (builds on) | `player_debut_final` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Calculates the difference in years between debut and final dates._

```sql
SELECT
  CAST(JULIANDAY('final_game') - JULIANDAY('debut') / 365 AS REAL) AS years
FROM player_debut_final
```

---

**Skill `player_stats`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name_first` |
| output columns | `player_name`, `games_played`, `runs`, `hits`, `home_runs` |
| source tables | `player`, `batting` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Aggregates player statistics from individual game records._

```sql
SELECT
    p.name_first AS player_name,
    SUM(b.g) AS games_played,
    SUM(b.r) AS runs,
    SUM(b.h) AS hits,
    SUM(b.hr) AS home_runs
FROM player AS p
JOIN batting AS b
    ON p.player_id = b.player_id
GROUP BY p.name_first
```

---

**Skill `top_player`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `name_first` |
| output columns | `player_name`, `max_score` |
| source tables | `batting`, `player` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Identifies the player with the highest combined score._

```sql
SELECT
    p.name_first AS player_name,
    SUM(b.r + b.h + b.hr + b.rbi + b.sb) AS max_score
FROM batting AS b
JOIN player AS p
    ON b.player_id = p.player_id
GROUP BY p.name_first
ORDER BY max_score DESC
LIMIT 1
```

---
