# SkillView-SQL — Continual Text-to-SQL with a Self-Growing Graph of Executable Views

A runnable prototype of the SkillView-SQL idea: instead of generating CTE *agent views*
per question and discarding them (AV-SQL), we **store validated views as nodes in a
self-growing dependency graph** and, for each new question, **retrieve-and-compose** what
already exists and **generate only what is missing**.

```
rewrite(Q) -> steps -> for each step:  retrieve(graph)  --hit-->  reuse view
                                          |--miss--> generate CTE -> validate -> insert(+edges)
compose chosen views -> final SQL -> execute
```

## Why this is run *without* an LLM here
This environment has **no LLM API keys** and **no Spider/BIRD/Spider 2.0 data** (gated /
multi-GB / cloud-warehouse). So the *generate-on-miss* step is backed by a deterministic
**view library** (`bench.py`) that stands in for the AV-SQL `CTEAgent`. This isolates and
measures the **graph mechanism** (retrieve / reuse / validate / compose / grow) against
**real execution results** on a real SQLite DB — reproducibly, with no network. The LLM
path drops in at one function (see *Integration* below) for real-benchmark runs.

## Files
| file | role | maps to AV-SQL stage |
|------|------|----------------------|
| `build_db.py` | builds a real seeded retail+HR SQLite DB (6 tables, 3k orders) | the database `D` |
| `core.py` | `ViewSpec`, `ViewGraph`, `retrieve` (+compatibility guard), `validate_view`, `compose_sql` | **the new memory layer** |
| `bench.py` | view library (10 skill-driven views) + 16-question sequential stream + gold SQL | Question Rewriting output + CTEAgent output |
| `run.py` | sequential harness, 3 configs, metrics | SQL Generation + evaluation |
| `plot.py` | learning-curve figure | — |

## Run
```bash
python -m skillview.run     # prints per-question trace + 3-config summary; writes results/
python -m skillview.plot    # results/learning_curve.png
```

## Results (this machine, 16-question stream, 10-view library)
| metric | (A) SkillView | (B) Baseline AV-SQL | (C) SkillView, guard OFF |
|---|---|---|---|
| Execution accuracy | **100.0%** | 100.0% | 93.8% |
| Exact view-reuse rate | **43.8%** | 0.0% | 50.0% |
| % questions with **no new CTE** | **43.8%** | 0.0% | 50.0% |
| Total CTE generations | **10** | 23 | 9 |
| Token proxy (gen) | **15,000** | 34,500 | 13,500 |
| Negative-reuse count | **0** | 0 | **1** |
| Final graph size | 10 views | 0 (discarded) | 9 |

**Takeaways.** (1) Memory cuts CTE generation **56.5%** (10 vs 23) with **no accuracy loss**
— the curve plateaus as the graph saturates while the baseline grows linearly. (2) The
**compatibility contract is load-bearing**: turning it off lets Q13 (“completed-only
monthly revenue”) wrongly reuse the all-orders `monthly_sales` view → 1 negative reuse →
accuracy drops to 93.8%. This is the empirical argument for the semantic-filter guard.

## The negative-reuse guard (`core.compatible`)
A stored view may be reused for a step only if: same skill category; required outputs are
exposed; grain is exact-or-finer; **and semantic filters match exactly**. The last clause
is what blocks reusing an all-orders aggregate for a completed-only question.

## Integration with the real AV-SQL pipeline (for Spider/BIRD/Spider 2.0)
Replace the deterministic instantiation in `run.build_view` with the real agents:
1. **Generate** — call `av_sql.cte_agent.CTEAgent` to produce the CTE body for the step.
2. **Generalize** — episodic→reusable (lift literals to params, drop final ORDER BY/LIMIT,
   keep keys/grain) before storing — see `prompt_templates/cte_categories/`.
3. **Validate** — `core.validate_view` already executes against the DB via `SqlExecEnv`.
4. **Embed** — swap the TF-IDF `_semantic_sim` for `all-MiniLM-L6-v2` (already a project dep).
5. **Persist** — one `ViewGraph` per `db_id`; evaluate **sequentially** per database
   (the harness in `run.run_config` is the template) so within-DB CTE reuse can occur.

## Evaluation protocol note
SkillView only shows reuse under a **sequential, per-database** protocol (graph empty at the
first question of a DB, grows after each). Report cold-start vs warm accuracy, exact-reuse
rate, %-no-new-CTE, avg-new-views/Q, token/runtime reduction vs question index, and
negative-reuse rate (all emitted by `run.py`).
