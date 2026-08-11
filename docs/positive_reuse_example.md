# Positive view-reuse in config A — a self-grown skill reused into a *correct* answer

The BEAVER config-A run had no meaningful reuse (its single reuse was a trivial projection that
didn't affect the result — see `beaver_A_reuse_example.md`). Config A's view-memory **does** fire
positively on **Spider 2.0-lite**. Here is a verified example, traced end-to-end: **when the skill was
built, in which question, its full saved node, the question that reused it, and its graph neighbours
after the run.**

Benchmark: Spider 2.0-lite · DB `IPL` · config A (schema-free rewrite + N×M + ReFoRCE, per-db run
`s2lApd_IPL`). The skill is `ball_events_batsman_level`.

---

## 1. When / where the skill was CONSTRUCTED

The skill was first generated at **`local021`** (the 3rd IPL question processed, `db_index = 2`):

> **`local021` (construction):** *"Could you calculate the average of the total runs scored by all
> strikers who have scored more than 50 runs in any single match?"* — **result: WRONG** (`correct =
> False`).

Honest nuance: the skill was **born inside a question the pipeline ultimately got wrong**. The
*view itself* is correct — it passed the free execution dry-run and was kept in the graph — but
`local021`'s final composition failed elsewhere. So a good building block can survive a bad answer.

## 2. The question that REUSED it (correctly)

One question later, **`local022`** (`db_index = 3`) retrieved and reused it:

> **`local022` (reuse):** *"Retrieve the names of players who scored no less than 100 runs in a match
> while playing for the team that lost that match."* — **result: CORRECT** (`correct = True`,
> `reused = 1`, `seed = 0`).

This is the only question recorded in the skill's `validated_on` — i.e. the L4 learning marked the
skill "validated" precisely because reusing it here produced the right answer.

## 3. The FULL saved skill (exact ViewSpec node in the graph)

```json
{
  "name": "ball_events_batsman_level",
  "category": "JOIN",
  "body_sql": "SELECT\n  b.match_id,\n  b.over_id,\n  b.ball_id,\n  b.innings_no,\n  b.striker,\n  bs.runs_scored\nFROM\n  ball_by_ball AS b\nLEFT JOIN\n  batsman_scored AS bs\nON\n  b.match_id = bs.match_id\n  AND b.over_id = bs.over_id\n  AND b.ball_id = bs.ball_id\n  AND b.innings_no = bs.innings_no",
  "source_tables": [
    "ball_by_ball",
    "batsman_scored"
  ],
  "output_columns": [
    "match_id",
    "over_id",
    "ball_id",
    "innings_no",
    "striker",
    "runs_scored"
  ],
  "grain": [
    "match_id",
    "over_id",
    "ball_id",
    "innings_no",
    "striker"
  ],
  "semantic_filters": {},
  "depends_on": [],
  "params": {},
  "description": "Denormalized ball-level events joined to the batsman runs events so each row is a specific ball delivery associated with the striker and the batsman runs scored on that delivery (if any). Keeps raw batsman runs separate from extras/wickets.",
  "validated_on": [
    "Retrieve the names of players who scored no less than 100 runs in a match while playing for the team that lost that match."
  ],
  "counter_examples": []
}
```

Its `body_sql`, rendered:

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

## 4. How `local022` consumed it (reused node → referenced CTE in the CORRECT query)

```sql
WITH ball_events_batsman_level AS (           -- <-- the REUSED node, verbatim
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
  FROM ball_events_batsman_level b                      -- <-- consumed here
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

## 5. Graph neighbours AFTER the run finished

At end of the IPL run the graph holds **26 views**. The skill's edges:

```
                         skill::JOIN
                             | INSTANTIATES
                             v
   (base tables) --> [ ball_events_batsman_level ]   depends_on: []   (a base-level JOIN view)
                             |
             DEPENDS_ON (two views build ON it)
             |------------------------------|
             v                              v
   [ player_match_runs ] (AGG)      [ baller_delivery_events ] (JOIN)
   depends_on:                      depends_on:
     ball_events_batsman_level        ball_events_batsman_level
     player_match_participation
```

- **INSTANTIATES:** `skill::JOIN → ball_events_batsman_level` (it lives under the JOIN capability).
- **DEPENDS_ON (outgoing):** none — it reads base tables `ball_by_ball` + `batsman_scored` directly.
- **DEPENDS_ON (incoming — the "related nodes"):** two later views build on it:
  - **`player_match_runs`** (AGG, grain `[match_id, striker, team_id]`) — *"per-player per-match batting
    totals, summing ball-level batsman runs"*; `depends_on = [ball_events_batsman_level,
    player_match_participation]`. (This is the CTE `local022` used.)
  - **`baller_delivery_events`** (JOIN, grain `[match_id, over_id, ball_id, innings_no, bowler]`) —
    *"one row per delivery with bowler, striker, runs, and extras"*; `depends_on =
    [ball_events_batsman_level]`.

So `ball_events_batsman_level` became a **shared foundation node**: a base-level ball×striker join that
two higher-level skills (`player_match_runs`, `baller_delivery_events`) were later built on top of —
exactly the compounding-reuse behaviour the view-memory is meant to produce.

## 6. Verification bar & honest scope

- A row counts as genuine positive reuse only if the reused node **appears and is consumed** in the
  *correct* final SQL (not merely tallied). Verified here (`ball_events_batsman_level AS (` is defined
  and read by `player_match_runs`). **7 config-A Spider2 questions** meet this bar.
- This is **online** (self-grown) reuse, `seed = 0` — built earlier in the same run, reused later. It
  fires on Spider 2.0-lite's broad, pattern-repeating schemas, not on BEAVER's warehouse questions.
- Provenance caveat worth keeping: the skill was first generated during a question that got the wrong
  answer (`local021`), then paid off on `local022`. The view-memory kept a correct building block even
  though the answer that spawned it was wrong.
