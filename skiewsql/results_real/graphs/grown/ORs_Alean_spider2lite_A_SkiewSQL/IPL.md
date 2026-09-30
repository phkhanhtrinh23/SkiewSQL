# Skill graph — `IPL` (2 skills)

**Skill `over_runs_conceded`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match_id`, `innings_no`, `over_id`, `bowler` |
| output columns | `match`, `innings`, `over`, `bowler`, `runs_conceded` |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `match_max_over_runs` |
| validated_on | — |
| counter_examples | 0 |

_total runs conceded per over per bowler per match_

```sql
SELECT
    b.match_id AS match,
    b.innings_no AS innings,
    b.over_id AS over,
    b.bowler AS bowler,
    SUM(COALESCE(bs.runs_scored, 0) + COALESCE(er.extra_runs, 0)) AS runs_conceded
FROM ball_by_ball AS b
LEFT JOIN batsman_scored AS bs
    ON b.match_id = bs.match_id
   AND b.over_id = bs.over_id
   AND b.ball_id = bs.ball_id
   AND b.innings_no = bs.innings_no
LEFT JOIN extra_runs AS er
    ON b.match_id = er.match_id
   AND b.over_id = er.over_id
   AND b.ball_id = er.ball_id
   AND b.innings_no = er.innings_no
GROUP BY b.match_id, b.innings_no, b.over_id, b.bowler
```

---

**Skill `match_max_over_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match` |
| output columns | `match`, `max_runs` |
| source tables | `over_runs_conceded` |
| depends_on (builds on) | `over_runs_conceded` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_maximum runs conceded in any single over within each match_

```sql
SELECT
    match,
    MAX(runs_conceded) AS max_runs
FROM over_runs_conceded
GROUP BY match
```

---
