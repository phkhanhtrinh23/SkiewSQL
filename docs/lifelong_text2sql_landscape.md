# Lifelong / memory-augmented Text-to-SQL — landscape, plan, and honest status

## 1. Related systems (2025–26)

| System | What it does | Comparable to us? |
|---|---|---|
| **MERIT** — *Learning to Retrieve: Dual-Level Long-Term Memory for Text-to-SQL Agents* (Snowflake AI Research + UIC, arXiv 2606.00547) | Episode-level + turn-level long-term memory, **RL-learned** retrieval policies + a Process Reward Model. SOTA on **BIRD-Interact**; transfers to **Spider2-Snow**. | **Closest competitor** — direct memory-reuse claim. But it's **interactive multi-turn** + **RL-trained**. |
| **Continual Learning of Domain Knowledge from Human Feedback in Text-to-SQL** (NeurIPS 2025, arXiv 2511.10674) | Distills **human NL feedback** into structured memory (join templates, agg logic, debug routines) for reuse. | Lifelong, but **human-in-the-loop**; we grow memory **autonomously**. Different regime. |
| **Memory Architectures for Multi-Turn Text-to-SQL: A Benchmark** (arXiv 2605.26394) | A **benchmark** for memory architectures in multi-turn text-to-SQL. | Useful as a shared eval, but multi-turn. |
| **Learning While Acting** (2606.04815), **Residual Skill Optimization for T2SQL Ensembles** (2605.21792) | Skill-library / online-lifelong angles. | Skill framing overlaps; not memory-of-views. |

**Our niche:** *single-turn, cross-question* reuse of **executable SQL views ("skills")**, grown
autonomously (no feedback, no RL). None of the above reuse *composable SQL relations* the way we do;
they reuse *experiences/facts/strategies*. This is a genuine differentiator, but it also means a
head-to-head needs care (see §3).

## 2. Zero-Mem (arXiv 2607.29377) — can we apply it? Honest.

*Zero-Mem: Zero-Token Memory Operations for LLM Agents* is **long-memory conversational QA**, not
text-to-SQL. Structures: an **entity–context graph** (relations across turns) + a **temporal
hierarchy** (session locality). Novelty: **memory ops cost zero LLM tokens** — retrieval + calibration
are deterministic; the LLM runs only for the final answer.

- ✅ **Adopt the principle** (zero-token / deterministic memory ops). Today our reuse spends LLM calls
  on `verify_reuse`/`choose_reuse` votes per sub-goal. We already have a deterministic guard
  (`sqlview.compatible`: category + grain + output). We can **drop the verify-LLM votes** and select
  reuse by embedding-retrieval + the structural guard, reserving the LLM for final generation. Cheaper,
  faster, and their "deterministic calibration discards conflicting evidence" ≈ our grain/output
  rejection.
- ❌ **Do NOT adopt the temporal hierarchy (the "tree").** It assumes a conversation with session
  locality. Our questions are **independent** — no temporal structure to hierarchy over. Forcing a
  time-tree onto SQL questions is fancy-but-doesn't-work.
- ⚠️ **The entity–context graph is redundant.** We already have a graph, and ours (a **DEPENDS_ON
  dependency DAG + skill-category** typing) is *better* suited to SQL composition than an entity-context
  graph. A skill **taxonomy tree** is possible but marginal (we already group by category + retrieve by
  embedding).

**Verdict:** steal the principle (deterministic zero-token reuse selection), not the architecture.

## 3. Plan (a) — benchmarking vs the memory systems

- **Code availability:** no clear *official* public repo found for MERIT (only a possibly-unrelated
  third-party repo); it is **RL-trained** (episode/turn retrieval policies + PRM), so faithful
  reproduction is heavy. The NeurIPS-2025 feedback system needs a human-feedback protocol we lack.
- **Decision (per your instruction):** **reproduce our own** comparable memory baseline rather than
  chase their code. Concretely, a *static-retrieval memory* and a *dynamic-retrieval memory* ablation
  of our own view-graph — which is exactly the "no-memory / static / dynamic" ladder MERIT reports
  against.
- **Shared benchmark:** **Spider2-Snow** (Snowflake) is the natural common ground (MERIT transfers to
  it; we already run Spider2-lite). Caveat: MERIT is *interactive*; our setting is single-turn
  cross-question — report both honestly, don't claim a like-for-like number.

## 4. Status (b) — N×M + view-memory wired into the Snowflake path

**Done (code):** `spider2sf.sf_table_blocks()` (per-table DDL blocks, sharded-collapse — replaces the
16k `render_sf_schema` truncation) and `sf_method.py` now branch on `--nxm`: schema-free rewrite →
`decompose_and_align` → per-sub-goal aligned schema via `table_catalog.render_selected`, plus
`--nxm/--max_subgoals/--reforce` CLI. Parses, imports, and reads the real Snowflake DDLs
(e.g. `GEO_OPENSTREETMAP_CENSUS_PLACES` = 67 tables, previously mostly truncated).

**Blocked (runtime):** the Snowflake account is **suspended** —
`000666 (57014): Your account is suspended due to lack of payment method.` So Spider2-Snow **cannot be
run live** until the account is reactivated. The code is ready; the blocker is billing, not the wiring.

**Next once Snowflake is live:** smoke `--nxm 1` on 2–3 tasks, then the full A vs baselines (+ the
static/dynamic memory ablations) on Spider2-Snow.
