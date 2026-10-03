# SkiewSQL — Continual Text-to-SQL with a Self-Growing Graph of Executable Views

**SkiewSQL** turns the throw-away *agent views* of AV-SQL into a **persistent, self-growing graph of validated, reusable CTE views**. AV-SQL regenerates every CTE per question and discards it (the stage that costs **77% of its tokens and 55% of its runtime**). SkiewSQL instead, for each new question, **retrieves and composes** the views it already has and **generates only what is missing** — then validates, stores, and connects the new views so later questions reuse them.

```
rewrite(Q,K) ─▶ per-chunk view proposal ─▶ for each sub-goal:
                                              retrieve(graph) ──hit──▶ reuse view
                                                   │
                                                   └─miss─▶ generate CTE (value-linked)
                                                            ─▶ execute-validate ─▶ store + edges
            ─▶ S_filtered ─▶ planner ─▶ SQL generator ─▶ execution-repair ─▶ semantic revisor
```

This package contains **two studies**:
1. a **real end-to-end study** on Spider / BIRD with a real LLM, real SQLite execution, and real token accounting (`llm/datasets/valuelink/sqlview/agents/realrun/analyze`).
2. a **controlled, deterministic mechanism study** (no LLM, no network) that isolates the graph machinery on a seeded retail DB (`core/bench/run/build_db/plot`).

## Files

| file | role |
|------|------|
| `llm.py` | OpenAI chat + embeddings with **real per-stage token accounting** |
| `datasets.py` | Spider/BIRD loaders, schema render, **schema compression + length-based chunking**, SQLite exec, Spider-style EX comparison |
| `valuelink.py` | **value linking**: sqlglot literal extraction + MinHash-LSH grounding to real DB cell values (edit + embedding similarity) |
| `sqlview.py` | embedding **retrieval** + the negative-reuse **compatibility guard** + execution-grounded **validation** + graph persistence |
| `core.py` | `ViewSpec` / `ViewGraph` (networkx. `INSTANTIATES` + `DEPENDS_ON` edges) + `compose_sql` |
| `agents.py` | the AV-SQL agents: rewriter, per-chunk view proposer (+ schema selection `J`), view generator, planner, SQL generator, execution revisor, **semantic revisor** |
| `realrun.py` | sequential per-DB harness (**SQLite**). Configs **A** (SkiewSQL online), **B** (baseline AV-SQL), **C** (no-guard), **S** (cold-start seed). Metrics. **Persists grown graphs** (see below) |
| `analyze.py` | learning-curve figures + markdown report |
| `coldstart.py` | **cold-start seed builder** (SQLite): 4-stage, leakage-safe (schema-only) library build → frozen seed graph for config **S**. Now also **skillifies** each seed view |
| `skillify.py` | turns a validated view into a **skill** (reuse contract: `when_to_use`, `output_schema`, grounded columns, `metric`, `composition`). `attach_skills` populates `ViewSpec.params`. CLI emits a full-markdown skill doc |
| `spider2lite.py` | Spider 2.0-lite **local-SQLite** subset loader + CSV-result scorer |
| `spider2sf.py`, `sf_method.py`, `coldstart_sf.py` | **Snowflake** backend: probe + method + seed builder (`describe`-based free validation, PAT auth) |
| `spider2bq.py`, `bq_method.py`, `coldstart_bq.py` | **BigQuery** backend: probe + method + seed builder (dry-run free validation, cost guard) |
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

The **only** difference between config A (SkiewSQL) and config B (baseline AV-SQL) is whether the view graph persists across a database's questions. Everything else is identical, so the A-vs-B deltas isolate the contribution of the persistent view memory.

## The negative-reuse guard (`sqlview.compatible`)

A stored view may be reused for a sub-goal only if: same skill category. Required outputs are exposed. Grain is exact-or-finer. **And intrinsic semantic filters match exactly**. The last clause blocks reusing an all-rows aggregate for a filtered-cohort question. Config **C** turns this guard off to measure the resulting negative reuse.

## Evaluation protocol (must be sequential & per-database)

Reuse can only occur if questions for a database arrive as a stream `Q₁ᴰ … Qₙᴰ`, with the graph empty at the first question of `D` and growing after each. We report: Execution Accuracy (**cold-start** = first question per DB vs **warm** = later), **exact view-reuse rate**, **% questions with no new CTE**, avg new views/Q, **real token counts** (per stage), **negative-reuse count**, and a **learning curve** (cumulative generations / tokens vs question index). All scored against gold-SQL execution on the real SQLite DB.

## Running the experiments

All commands are run as modules from the **repo root** (the parent of `skiewsql/`). Results use the structured layout documented in `skiewsql/results_real/README.md`.

### 0. Prerequisites

```bash
export OPENAI_API_KEY=sk-...          # required for every LLM run
```

- **SQLite (Spider / BIRD / spider2lite):** local `.sqlite` DBs on disk. Paths are set in `datasets.py` (`SPIDER_ROOT`, `BIRD_DEV_ROOT`) and `spider2lite.py` (`SQLITE_ROOT`).
- **Snowflake:** a credential JSON + PAT file (`spider2sf.py: CRED`, `PAT`). Auth uses the PAT as the password. Warehouse defaults to `COMPUTE_WH_PARTICIPANT`.
- **BigQuery:** a service-account JSON (`spider2bq.py: CRED`).

Models: default `gpt-5-mini` (a reasoning model — no custom temperature. Runs are **not** deterministic, so expect run-to-run accuracy noise of a few points).

### The configs

| flag | config | meaning |
|------|--------|---------|
| `--configs B` | **B — AV-SQL** | plain per-question CTEs, **no memory** (graph reset each question). The faithful baseline. |
| `--configs A` | **A — SkiewSQL online** | graph **persists** across a DB's questions (starts empty, grows). |
| `--configs S` (with `--seed_tag`/`--seed_dir`) | **S — cold-start seed** | graph is **preloaded** from a frozen seed library (the paper's method). |
| `--configs C` | **C — no-guard** | A with the compatibility guard off (measures negative reuse). |
| `--verify N` | Layer-3 gate | `N` skeptical reuse-verifiers (majority-allow). `0` = off. Config S/A typically use `--verify 1`+. |

### Adaptive architecture (recommended)

`--architecture auto` implements semantic difficulty routing:

1. **easy**: direct final SQL over at most two selected tables. No view is retrieved, generated, or stored.
2. **moderate**: graph-enabled AV-SQL N×1—the complete rewrite is sent to every schema chunk, and each chunk request searches the saved graph before generating a missing exploratory CTE.
3. **hard**: dependency-aware N×M for multiple grains/cohorts, ratios, nested aggregation, windows, set operations, recursion, or other dependent intermediate relations. Subgoals declare `depends_on`, join keys, relationship, and whether they may reread base tables.

Join count alone does not set difficulty. A clear foreign-key join can be easy, while a zero-join ratio against a group average can be hard. Uncertain routing decisions conservatively become moderate AV-SQL N×1.

The comparison modes are `--architecture nx1` for original AV-SQL and `--architecture nxm` for forced dependency N×M. `legacy` remains available. When N×1 uses a nonempty graph, a detailed contract is created only for conservative skill retrieval. A safe hit is reused. On an uncertain contract or retrieval miss, the original AV-SQL chunk agent runs unchanged with the complete rewrite and original chunk schema. No-graph N×1 performs no contract calls. The retired focused-holistic and AV-SQL-2 ablations are no longer exposed. `--chunk_budget` controls the original schema partition. Every result row records the route, chunk count, alignment-call count, retrieval-contract metrics, and selected-schema size. `--focused_budget` is retained only so historical experiment commands still parse. It does not classify question difficulty. The deprecated `--nx1 1` and `--nxm 1` flags still work and override `--architecture`.

```bash
python -m skiewsql.realrun --dataset spider2lite --dbs top:30 --limit 20 \
  --configs A,B --architecture auto --tag adaptive
```

The same selector is exposed by `beaver_method`, `bq_method`, `sf_method`, and `livesql_method`.

The controlled four-way local benchmark and raw outputs are in `results_real/benchmarks/architecture/REPORT.md`, including a graph-enabled run of 20 questions per dataset and architecture. It is a low-budget/local-model stress test, not a production headline result.

### 1. SQLite — Spider / BIRD / spider2lite

```bash
# --- config A vs B vs C (online memory, no seed) ---
python -m skiewsql.realrun --dataset spider --dbs top:4 --limit 20 --configs A,B,C --tag v2
python -m skiewsql.realrun --dataset bird   --dbs top:4 --limit 20 --configs A,B,C --tag v2
python -m skiewsql.analyze --tag v2 --dataset spider          # -> figures + report

# --- config S (cold-start seed): build the library, then run S vs B ---
# Step 1: build the frozen seed graphs. This is leakage-safe and also skillifies each view.
python -m skiewsql.coldstart --dataset spider2lite --dbs top:30 --tag seed --max_per_cat 2
#   -> results_real/graphs/seed/seed_spider2lite/<db>.json
# Step 2: run S (seed) vs B (baseline) with value-linking (LSH) on
python -m skiewsql.realrun --dataset spider2lite --dbs top:30 --limit 20 \
    --configs B,S --seed_tag seed --verify 1 --tag s2run
#   S loads results_real/graphs/seed/seed_spider2lite. --seed_dir overrides the convention.
```

`--dbs` takes `top:N` (the N DBs with the most questions) or an explicit comma list.

### 2. Snowflake (native cloud)

```bash
# Step 1: build skill seeds (describe-validated, FREE — no warehouse compute)
python -m skiewsql.coldstart_sf --tag seedsf --max_per_cat 2        # all sf DBs. Alternatively, use --dbs CRYPTO,PATENTS.
#   -> results_real/graphs/seed/seedsf_snowflake/<db>.json
# Step 2: B (AV-SQL, no skill) and S (SkiewSQL + skill seed)
python -m skiewsql.sf_method --dbs CRYPTO,THELOOK_ECOMMERCE --n 300 --verify 0 --tag sf_B
python -m skiewsql.sf_method --dbs CRYPTO,THELOOK_ECOMMERCE --n 300 --verify 3 \
    --seed_dir skiewsql/results_real/graphs/seed/seedsf_snowflake --tag sf_S
# quick direct-SQL floor (single-shot, no view pipeline):
python -m skiewsql.spider2sf --n 20 --model gpt-5-mini --tag sfprobe
```

### 3. BigQuery (native cloud)

```bash
python -m skiewsql.coldstart_bq --tag seedbq --max_per_cat 2        # all bq DBs. Alternatively, use --dbs stackoverflow,ga360.
python -m skiewsql.bq_method --dbs stackoverflow,ga360 --n 300 --verify 0 --max_gb 20 --budget_tib 10 --tag bq_B
python -m skiewsql.bq_method --dbs stackoverflow,ga360 --n 300 --verify 3 --max_gb 20 --budget_tib 10 \
    --seed_dir skiewsql/results_real/graphs/seed/seedbq_bigquery --tag bq_S
#   --max_gb caps each query scan. --budget_tib caps cumulative scanning for free-tier safety.
```

### Skills (inspect / generate)

`coldstart*` **auto-skillifies** each seed view (contract stored in `ViewSpec.params`: `when_to_use`, `output_schema`, `grounded_columns`, `metric`, `composition`). To emit a full human-readable skill doc for one view:

```bash
python -m skiewsql.skillify --seed_graph skiewsql/results_real/graphs/seed/seed_spider2lite/f1.json \
    --view driver_season_rank --dialect SQLite          # -> SKILL_<view>.md
```

### Grown-graph persistence (the learning that survives a run)

Config **A/S** now **save the grown graph** after each DB — the online-added views **plus** each reused view's `validated_on` (questions it answered correctly) and `counter_examples` (questions where reusing it was a bad hit). Written to:

- SQLite: `results_real/graphs/grown/<tag>_<dataset>_<config>/<db>.json`
- Snowflake / BigQuery: `results_real/runs/{snowflake,bigquery}/<tag>_*_graphs.json`

### Outputs

Per run: `results_real/runs/sqlite/<dataset>/<tag>_<dataset>_<config>.json` (SQLite) or `results_real/runs/{snowflake,bigquery}/<tag>_{sf,bq}_method.json` (cloud), each with per-question rows, `pred_sql`, full skill/CTE traces, reuse/seed-reuse/negative-reuse counts, accuracy, and token/cost accounting.

### Controlled mechanism study (no LLM / no network)

```bash
python -m skiewsql.run
```

### Sequential runs (avoid concurrency crashes)

Running many heavy jobs at once (each loads an embedding model + hammers the LLM API) can exhaust memory / rate limits. Run backends **sequentially** (e.g. `cmd1 && cmd2 && cmd3`), not in parallel.

## Results

Full write-up in [`RESULTS.md`](RESULTS.md). Figures + per-question traces in `results_real/` (regenerated by `analyze.py`). Real LLM (`gpt-4o-mini`), real SQLite execution, real token counts.

**Spider (60 Q, A vs B):** **equal accuracy** (50/60 vs 49/60 — a 1-question tie within LLM noise), view-reuse **31.5%**, **38.5% fewer CTE generations** (75 vs 122), 6.7% fewer tokens — the baseline's generation curve grows linearly while SkiewSQL's flattens as the graph saturates.

**BIRD (45 Q, A vs B):** accuracy tie (21/45 vs 21/45), view-reuse only **8.3%** → savings vanish.

**Key finding:** SkiewSQL is a **reuse/efficiency** mechanism, not an accuracy mechanism — it delivers **the same answers more cheaply** by not re-deriving validated intermediate relations. The savings scale with **question-stream homogeneity** (large on Spider's related questions, ~zero on BIRD's heterogeneous, evidence-heavy ones) and it never regressed accuracy here (guard on: A ≥ B by 0–1 questions). Intended regime: continual Text-to-SQL over a database that serves a long stream of related questions.
