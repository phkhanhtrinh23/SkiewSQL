# Positive view-reuse in config A — a self-grown skill reused into a *correct* answer

The BEAVER config-A run had no meaningful reuse (its single reuse was a trivial projection that
didn't affect the result — see `beaver_A_reuse_example.md`). Config A's view-memory **does** fire
positively on **Spider 2.0-lite**, where the schema breadth and repeated question patterns let a
self-grown "skill" get reused. Here is a verified example — the reused view is not just *counted* but
genuinely **appears and is used** in the final, correct query.

## Example — Spider 2.0-lite · `IPL` · `local022` (config A, schema-free rewrite + N×M + ReFoRCE)

**Question.** *Retrieve the names of players who scored no less than 100 runs in a match while playing
for the team that lost that match.*

**Outcome.** `correct = True`, `reused = 1` (non-trivial), `seed = 0` — the reused view was **grown
online** during the same run, from an earlier IPL question.

### The reused skill (grown earlier, retrieved for this question)
`ball_events_batsman_level` — category **JOIN**, grain `[match_id, over_id, ball_id, innings_no, striker]`:

```sql
SELECT
  b.match_id, b.over_id, b.ball_id, b.innings_no, b.striker,
  bs.runs_scored
FROM ball_by_ball AS b
LEFT JOIN batsman_scored AS bs
  ON  b.match_id  = bs.match_id
  AND b.over_id   = bs.over_id
  AND b.ball_id   = bs.ball_id
  AND b.innings_no = bs.innings_no
```

This is a genuine (non-trivial) building block: it denormalises a cricket delivery to *(ball →
striker, runs)*. On `local022` the retrieval + compatibility guard + LLM verify accepted it for the
"ball-level events" sub-goal instead of regenerating it.

### The final, correct query — the reused view is an actual CTE that later steps build on
```sql
WITH ball_events_batsman_level AS (           -- <-- REUSED verbatim
  SELECT b.match_id, b.over_id, b.ball_id, b.innings_no, b.striker, bs.runs_scored
  FROM ball_by_ball AS b
  LEFT JOIN batsman_scored AS bs
    ON b.match_id=bs.match_id AND b.over_id=bs.over_id AND b.ball_id=bs.ball_id AND b.innings_no=bs.innings_no
),
player_match_participation AS (
  SELECT pm.match_id, pm.player_id, pm.team_id, pm.role FROM player_match pm
),
player_match_runs AS (
  SELECT b.match_id, b.striker AS player_id, pm.team_id, SUM(b.runs_scored) AS total_runs
  FROM ball_events_batsman_level b                      -- <-- REUSED view consumed here
  LEFT JOIN player_match_participation pm
    ON b.match_id = pm.match_id AND b.striker = pm.player_id
  GROUP BY b.match_id, b.striker, pm.team_id
)
SELECT DISTINCT p.player_name
FROM player_match_runs pmr
JOIN player_match_participation pmp
  ON pmp.match_id = pmr.match_id AND pmp.player_id = pmr.player_id
...
```

`player_match_runs` reads **`FROM ball_events_batsman_level`** — so the reused skill is a real
dependency of the correct answer, not a dead CTE. The pipeline reused it (`gen` for that sub-goal was
saved), aggregated runs per (match, striker, team) on top of it, then filtered to ≥100-run innings on
the losing team.

## Why this one counts (and how it was verified)
A row is only a *genuine* positive reuse if the reused view is **referenced** in the final SQL, not
merely tallied. We verified: `ball_events_batsman_level AS (` is defined and then **read by a later
CTE**. Across the config-A Spider2 runs, **7 questions** meet this strict bar (reused view appears and
is consumed in the *correct* query), e.g.:

| qid | db | reused skill (used in correct SQL) | config |
|---|---|---|---|
| `local022` | IPL | `ball_events_batsman_level` | new schema-free A |
| `local039` | Pagila | `film_categories` | new schema-free A |
| `local026` | IPL | `over_runs` | A (relaxed) |
| `local193` | sqlite-sakila | `customer_total_ltv` | A (relaxed) |
| `local228` | IPL | `season_matches` | A (relaxed) |

## Honest scope
- This is **online** (self-grown) reuse, `seed = 0` — a skill built earlier in the same run and reused
  later. It shows the view-memory working *within* a session.
- It fires on **Spider 2.0-lite** (broad schemas, repeated ball-level / customer-level patterns), not
  on BEAVER's warehouse questions in config A.
- Cross-session **seed** reuse (the cold-start library) fires most on Spider2 config S — separate from
  this config-A example.
