# SkiewSQL — Continual Text-to-SQL with a Self-Growing Graph of Executable Views

**SkiewSQL** turns the throw-away *agent views* of AV-SQL into a **persistent, self-growing
graph of validated, reusable CTE views**. AV-SQL regenerates every CTE per question and
discards it (the stage that costs **77% of its tokens and 55% of its runtime**). SkiewSQL
instead, for each new question, **retrieves and composes** the views it already has and
**generates only what is missing** — then validates, stores, and connects the new views so
later questions reuse them.

```
rewrite(Q,K) ─▶ per-chunk view proposal ─▶ for each sub-goal:
                                              retrieve(graph) ──hit──▶ reuse view
                                                   │
                                                   └─miss─▶ generate CTE (value-linked)
                                                            ─▶ execute-validate ─▶ store + edges
            ─▶ S_filtered ─▶ planner ─▶ SQL generator ─▶ execution-repair ─▶ semantic revisor
```

This package contains **two studies**:
1. a **real end-to-end study** on Spider / BIRD with a real LLM, real SQLite execution, and
   real token accounting (`llm/datasets/valuelink/sqlview/agents/realrun/analyze`);
2. a **controlled, deterministic mechanism study** (no LLM, no network) that isolates the
   graph machinery on a seeded retail DB (`core/bench/run/build_db/plot`).

## Files

| file | role |
|------|------|
| `llm.py` | OpenAI chat + embeddings with **real per-stage token accounting** |
| `datasets.py` | Spider/BIRD loaders, schema render, **schema compression + length-based chunking**, SQLite exec, Spider-style EX comparison |
| `valuelink.py` | **value linking**: sqlglot literal extraction + MinHash-LSH grounding to real DB cell values (edit + embedding similarity) |
| `sqlview.py` | embedding **retrieval** + the negative-reuse **compatibility guard** + execution-grounded **validation** + graph persistence |
| `core.py` | `ViewSpec` / `ViewGraph` (networkx; `INSTANTIATES` + `DEPENDS_ON` edges) + `compose_sql` |
| `agents.py` | the AV-SQL agents: rewriter, per-chunk view proposer (+ schema selection `J`), view generator, planner, SQL generator, execution revisor, **semantic revisor** |
| `realrun.py` | sequential per-DB harness; configs **A** (SkiewSQL), **B** (baseline AV-SQL), **C** (no-guard); metrics |
| `analyze.py` | learning-curve figures + markdown report |
| `bench.py`,`run.py`,`build_db.py`,`plot.py` | the controlled, no-LLM mechanism study |

## AV-SQL fidelity (this baseline is a faithful reimplementation)

| AV-SQL component | SkiewSQL status |
|---|---|
| Stage 1 — Question Rewriting → structured tuple, **propagated downstream** | ✅ `rewrite_question` |
| Stage 2 — length-based **schema chunking** under token budget `B` | ✅ `datasets.chunk_schema` |
| Stage 2 — **schema compression** (~10× near-dup clustering) | ✅ `datasets.compress_schema` |
| Stage 2 — per-chunk view agents + JSON **schema selection `J`** → `S_filtered` | ✅ `propose_views` (union of selections) |
| Stage 2 — **value linking** (literal extraction + MinHash-LSH, τ_edit/τ_semantic) | ✅ `valuelink.ValueIndex` |
| Stage 2 — view **execution-validation** loop (T_max) | ✅ `_generate_view` + `sqlview.validate_view` |
| Stage 3 — **Planner** | ✅ `planner` |
| Stage 3 — SQL generator + **execution-repair** loop (T_max=5) | ✅ `compose_final` + `revise_sql` |
| Stage 3 — **Revisor** (semantic verification pass) | ✅ `semantic_revise` |
| Zero-shot, no in-context exemplars | ✅ |
| Decoding temperature 1.0 | ⚠️ we use **temp=0** for a deterministic memory ablation (single deliberate deviation) |

The **only** difference between config A (SkiewSQL) and config B (baseline AV-SQL) is whether
the view graph persists across a database's questions. Everything else is identical, so the
A-vs-B deltas isolate the contribution of the persistent view memory.

## The negative-reuse guard (`sqlview.compatible`)

A stored view may be reused for a sub-goal only if: same skill category; required outputs are
exposed; grain is exact-or-finer; **and intrinsic semantic filters match exactly**. The last
clause blocks reusing an all-rows aggregate for a filtered-cohort question. Config **C** turns
this guard off to measure the resulting negative reuse.

## Evaluation protocol (must be sequential & per-database)

Reuse can only occur if questions for a database arrive as a stream `Q₁ᴰ … Qₙᴰ`, with the graph
empty at the first question of `D` and growing after each. We report: Execution Accuracy
(**cold-start** = first question per DB vs **warm** = later), **exact view-reuse rate**,
**% questions with no new CTE**, avg new views/Q, **real token counts** (per stage),
**negative-reuse count**, and a **learning curve** (cumulative generations / tokens vs question
index). All scored against gold-SQL execution on the real SQLite DB.

## Run

```bash
# real end-to-end (needs OPENAI_API_KEY; Spider/BIRD SQLite DBs on disk)
python -m skiewsql.realrun --dataset spider --dbs world_1,dog_kennels --limit 20 --configs A,B,C --tag v2
python -m skiewsql.realrun --dataset bird   --dbs financial,superhero  --limit 15 --configs A,B,C --tag v2
python -m skiewsql.analyze --tag v2 --dataset spider     # -> figures + report in results_real/

# controlled mechanism study (no LLM / no network)
python -m skiewsql.run
```

## Results

Full write-up in [`RESULTS.md`](RESULTS.md); figures + per-question traces in `results_real/`
(regenerated by `analyze.py`). Real LLM (`gpt-4o-mini`), real SQLite execution, real token counts.

**Spider (60 Q, A vs B):** **equal accuracy** (50/60 vs 49/60 — a 1-question tie within LLM
noise), view-reuse **31.5%**, **38.5% fewer CTE generations** (75 vs 122), 6.7% fewer tokens —
the baseline's generation curve grows linearly while SkiewSQL's flattens as the graph saturates.

**BIRD (45 Q, A vs B):** accuracy tie (21/45 vs 21/45), view-reuse only **8.3%** → savings vanish.

**Key finding:** SkiewSQL is a **reuse/efficiency** mechanism, not an accuracy mechanism — it
delivers **the same answers more cheaply** by not re-deriving validated intermediate relations.
The savings scale with **question-stream homogeneity** (large on Spider's related questions,
~zero on BIRD's heterogeneous, evidence-heavy ones) and it never regressed accuracy here (guard
on: A ≥ B by 0–1 questions). Intended regime: continual Text-to-SQL over a database that serves a
long stream of related questions.
