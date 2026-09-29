# Skill graph — `IPL` (2 skills)

**Skill `over_runs`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `match`, `innings`, `over` |
| output columns | `match`, `innings`, `over`, `runs_conceded` |
| source tables | `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `max_over_candidates` |
| validated_on | — |
| counter_examples | 0 |

_total runs conceded per over within each match_

```sql
SELECT 
    match,
    innings,
    over,
    SUM(runs_conceded) AS runs_conceded
FROM (
    SELECT match_id AS match, innings_no AS innings, over_id AS over, SUM(runs_scored) AS runs_conceded FROM batsman_scored GROUP BY match_id, innings_no, over_id
    UNION ALL
    SELECT match_id AS match, innings_no AS innings, over_id AS over, SUM(extra_runs) AS runs_conceded FROM extra_runs GROUP BY match_id, innings_no, over_id
)
GROUP BY match, innings, over
```

---

**Skill `max_over_candidates`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `match`, `innings`, `over`, `runs_conceded` |
| output columns | `match`, `innings`, `over`, `bowler`, `runs_conceded` |
| source tables | `over_runs`, `ball_by_ball` |
| depends_on (builds on) | `over_runs` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_joins over-level run totals with match-level maximums, filters to only overs matching the match maximum, and attaches the bowler who delivered the over_

```sql
SELECT 
    o.match,
    o.innings,
    o.over,
    MAX(b.bowler) AS bowler,
    o.runs_conceded
FROM over_runs o
JOIN ball_by_ball b ON o.match = b.match_id AND o.innings = b.innings_no AND o.over = b.over_id
WHERE o.runs_conceded = (
    SELECT MAX(r.runs_conceded)
    FROM over_runs r
    WHERE r.match = o.match
)
GROUP BY o.match, o.innings, o.over, o.runs_conceded
```

---
