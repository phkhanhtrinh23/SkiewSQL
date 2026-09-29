# Skill graph — `IPL` (1 skills)

**Skill `chunk_view_0`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | — |
| output columns | — |
| source tables | `ball_by_ball`, `batsman_scored`, `extra_runs` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Task: Find the top 3 bowlers who, when considering only overs that were the maximum-scoring over(s) within their match, conceded the largest number of runs in a single over across all matches; for eac_

```sql
SELECT
  b.match_id,
  b.over_id,
  b.team_bowling,
  b.bowler,
  SUM(
    COALESCE(bs.runs_scored,0) + COALESCE(er.extra_runs,0)
  ) AS runs_in_over
FROM ball_by_ball b
LEFT JOIN batsman_scored bs
  ON b.match_id = bs.match_id
  AND b.over_id = bs.over_id
  AND b.ball_id = bs.ball_id
  AND b.innings_no = bs.innings_no
LEFT JOIN extra_runs er
  ON b.match_id = er.match_id
  AND b.over_id = er.over_id
  AND b.ball_id = er.ball_id
  AND b.innings_no = er.innings_no
GROUP BY
  b.match_id,
  b.over_id,
  b.team_bowling,
  b.bowler
```

---
