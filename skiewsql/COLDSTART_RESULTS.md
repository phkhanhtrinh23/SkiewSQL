# SkiewSQL Cold-Start Seed Graphs — Results

**Goal.** Remove SkiewSQL's *cold start*: instead of beginning each database with an empty
view graph and paying to generate every CTE for the first questions, we **pre-build a frozen
graph of validated, reusable CTE views from the schema alone** (no test questions, no gold SQL)
and load it as the initial memory. New CTEs generated later, during evaluation, are reported
separately as *online growth*.

All numbers are **real**: real `gpt-5-mini` (a reasoning model), real SQLite execution, real
API token counts. Execution accuracy (EX) is scored against gold — Spider/BIRD via gold-SQL
result comparison, Spider2-lite via the official gold **result-CSV** comparison.

**TL;DR.** The cold-start seed (S) delivers the **most view reuse and the fewest CTE generations
at parity-or-better accuracy** on both datasets, and reuse is available from question #0. Its
marginal value is **largest on hard, heterogeneous streams (Spider2)** — there, empty-start
SkiewSQL earns **0% reuse** and even generates *more* CTEs than the no-memory baseline, so the
seed is the *only* thing that makes persistent memory pay off. The apparent token penalty in the
first A/B/S runs was **not** a small-sample artifact and **not** intrinsic to seeding — it was a
fixable implementation detail (injecting the *whole* graph into each generation prompt). Fixing
it (inject only the top-k relevant views, §4) flips the seed config to **8.4% fewer tokens than
baseline** on a long stream. Model note: `gpt-5-mini` only allows default temperature, so this is
not a deterministic ablation; small accuracy deltas are within noise.

---

## 1. What was built

| file | role |
|------|------|
| `coldstart.py` | the cold-start builder — Prompt A (schema analysis) → B (candidate CTE generation, schema-grounded) → C (execution-grounded validation + LLM repair + dedup) → D (register `ViewSpec` nodes + `DEPENDS_ON` edges); persists one frozen graph per DB via `sqlview.save_graph`. Never sees questions/gold (data-leakage safe). |
| `realrun.py` (config **S**) | new configuration that loads the frozen seed graph as initial memory, then grows online; tracks **seed-vs-online** reuse separately. |
| `sqlview.compatible` | column-name matching normalized (case + non-alphanumerics) so the online proposer's aliases match seeded views. |
| `llm.py` | reasoning-model support for `gpt-5-mini` (`max_completion_tokens`, no custom temperature, `reasoning_effort="minimal"`). |
| `spider2lite.py` | loader for the local-SQLite subset of Spider 2.0-lite + a result-CSV scorer copying Spider2's official `compare_pandas_table` comparison verbatim. |

### Configurations compared (identical agents; only the memory differs)
- **A · SkiewSQL** — graph starts **empty** per DB, grows online (the original SkiewSQL).
- **B · Baseline AV-SQL** — graph reset before **every** question (generate every CTE, discard).
- **S · Cold-start seed** — graph starts as the **frozen pre-built seed**, then grows online.

The A-vs-S delta isolates the value of pre-building; the S/A-vs-B delta isolates memory itself.

### The cold-start builder, mapped to the prompt package
Prompt A (`analyse_schema`) classifies tables (entity/fact/dimension/bridge/hierarchy/archive),
grain, keys, temporal/versioning columns, safe join paths, and supported categories — from DDL
+ FKs + sample rows + a light profile (row counts + low-cardinality enum values). Prompt B
(`generate_candidates`) emits reusable CTE bodies across the ten categories
(SEL/NORM/AGG/JOIN/RANK/WIN/RESHAPE/REC/SET/SEM), **grounded in the real schema** and aliasing
pass-through columns to their **exact schema names** (critical: otherwise the online proposer's
column requests never match the seed and reuse is 0). Prompt C is done in code:
`sqlview.validate_view` executes each candidate (with its dependency closure) against the real
SQLite DB and checks declared outputs exist; failures get up to 3 LLM repairs; duplicates
(same category+outputs+grain) are pruned. Prompt D registers survivors into a `ViewGraph`
with `DEPENDS_ON` edges extracted from declared `input_ctes`.

---

## 2. Spider (3 DBs × 20 Q = 60/config; world_1, dog_kennels, student_transcripts_tracking)

Seed graphs: world_1 = 10 views, dog_kennels = 10, student_transcripts_tracking = 11.

| metric | A · SkiewSQL | B · Baseline | **S · Cold-start seed** |
|---|---|---|---|
| Execution accuracy | 73.3% | 70.0% | 71.7% |
| Cold-start EX (Q#0/db) | 66.7% | 66.7% | 66.7% |
| Warm EX (later Qs) | 73.7% | 70.2% | 71.9% |
| Exact view-reuse rate | 22.5% | 0% | **28.5%** |
| **Seed reuse (from Q#0)** | 0% | 0% | **10.6%** |
| % Q with no new CTE | 1.7% | 0% | **8.3%** |
| **Total CTE generations** | 137 | 179 | **128** |
| Avg new views / Q | 2.28 | 2.98 | **2.13** |
| Real total tokens | 790,391 | 718,447 | 794,659 |
| Negative-reuse count | 7 | 0 | 9 |

**Reads:**
- **S · seed vs B · baseline** — CTE generations 128 vs 179 → **51 fewer (28.5%)**; reuse 28.5%
  (10.6% from seeds available at question #0) vs 0%; accuracy 71.7% vs 70.0%.
- **S · seed vs A · empty-start** — **9 fewer generations (6.6%)**, and **5× more
  zero-generation questions** (8.3% vs 1.7%): the seed answers sub-goals from question #0 that A
  must generate. Accuracy is a tie (71.7% vs 73.3%, within run-to-run noise).
- **Honest token caveat.** Neither memory config saves total tokens — S and A use ~10% **more**
  than baseline B. The per-stage breakdown shows why: baseline B makes *more* generate calls
  (179) but each is cheap, while A/S make *fewer* calls (128) yet each `generate`/`plan`/`compose`
  prompt carries the growing graph as context, so the `generate` stage costs *more* (A 360k /
  S 368k vs B 300k tokens). **Memory shifts cost from generation *count* to prompt *size*.**
  This differs from the original AV-SQL paper's gpt-4o-mini finding and is a real, model- and
  implementation-dependent result. Fix for future work: inject only the *retrieved-relevant*
  views into generation prompts, not the whole graph.

**Takeaway.** The cold-start seed delivers the **highest reuse and the fewest CTE generations at
parity accuracy**, and eliminates cold-start generation (reuse from Q#0) — its intended effect.
The token metric does not improve because of graph-context prompt overhead.

Figures: `results_real/exp1seed_spider_gen_curve.png`, `..._token_curve.png`; full table +
per-stage tokens in `results_real/exp1seed_spider_report.md`.

---

## 3. Spider 2.0-lite (local-SQLite subset — the hard benchmark)

**Feasibility.** Spider 2.0's BigQuery/Snowflake tasks need cloud credentials, but its
**`local*` subset runs on local SQLite**: 135 questions across 30 DBs, all with a SQLite DB
and a gold result CSV. These are much harder — analytics questions with stacked CTEs, window
functions, RFM/moving-average logic — i.e. exactly the regime agentic views target. We score
with Spider2's official column-subset comparison (1e-2 tolerance, `ignore_order`,
`condition_cols`, multi-gold variants), validated at 9/10 gold self-consistency.

Seed graphs (schema-only): bank_sales_trading = 11 views, IPL = 10, city_legislation = 8.
Run: 3 DBs × 5 Q = 15/config.

| metric | A · SkiewSQL | B · Baseline | **S · Cold-start seed** |
|---|---|---|---|
| Execution accuracy | 33.3% | 26.7% | **40.0%** |
| Warm EX (later Qs) | 41.7% | 33.3% | **50.0%** |
| Exact view-reuse rate | 0% | 0% | **8.9%** |
| Seed reuse (from Q#0) | 0% | 0% | **8.9%** |
| Total CTE generations | 43 | 41 | **36** |
| Avg new views / Q | 2.87 | 2.73 | **2.40** |
| Real total tokens | 369,254 | 371,985 | 404,050 |
| Negative-reuse count | 0 | 0 | 1 |

**This is the strongest case for the cold-start seed.** Spider2's `local*` questions are short
per-DB streams (5 Q) of highly *heterogeneous*, bespoke analytics queries. Consequences:
- **Empty-start SkiewSQL (A) gets 0% reuse** — its online memory never accumulates a matching
  view within such a short, diverse stream. Worse, A generates *more* CTEs than the baseline
  (43 vs 41): the graph it carries is dead weight (inflated prompts, no reuse payoff).
- **The cold-start seed (S) is the *only* source of reuse (8.9%)**, cutting generations to the
  fewest of any config (36; −16% vs A, −12% vs B) and posting the highest accuracy (40.0% vs
  33.3% / 26.7%; ~1–2 questions, directionally positive).

So the seed's marginal value is **largest exactly where online accumulation fails** — short,
heterogeneous streams. On Spider (long, homogeneous streams) A already reached 22.5% online
reuse, so the seed added less at the margin; on Spider2, the seed rescues reuse that memory alone
never earns. (Token overhead recurs: S's `generate` stage rises to 53% of tokens, 215k vs ~181k,
from carrying the seed graph in prompts.) Absolute EX is high for spider2-lite because the
`local*` subset is its easier tier and `gpt-5-mini` is strong; the informative axis is the
reuse / generation-cost contrast across A/B/S. Report: `results_real/exp1seed_spider2lite_report.md`.

---

## 4. The token overhead was a prompt-bloat artifact — and it's fixable

The A/B/S runs showed S using ~8–10% *more* total tokens than baseline. We traced this precisely:
on Spider2 the entire increase (+34,894 of S's +34,796 tokens) sits in the **`generate`** stage,
because `generate_view` injected the **whole graph** as "views you may build on." Baseline B
resets its graph every question (always ~3 views → constant prompt size), but A/S carry a graph
that **grows with the stream**, so each generation prompt gets bigger as questions accrue.

We tested this on a **long homogeneous stream** — `world_1`, 40 sequential questions — comparing
B, S with whole-graph injection, and S with **selective injection** (`--gen_topk 6`: only the 6
views most embedding-similar to the sub-goal are offered to the generator).

| config | total tokens | tok/Q | early-10 → late-10 | slope | CTE gens | reuse | EX |
|---|---|---|---|---|---|---|---|
| B · baseline (no memory) | 370,847 | 9,271 | 9.5k → 8.5k | flat | 119 | 0% | 75.0% |
| S · seed, **whole-graph** inject | 438,074 | 10,951 | 9.6k → **10.2k** | **rising** | 68 | 43.3% | 72.5% |
| S · seed, **top-k** inject (fix) | **339,526** | **8,488** | 9.2k → **7.6k** | **falling** | 74 | 37.3% | **77.5%** |

**Findings (see `results_real/longstream_token_curve.png`):**
- **Baseline B is flat** (~9.3k tok/Q, no stream dependence), confirming the per-question cost
  model. Whole-graph **S rises** over the stream (9.6k → 10.2k, peaking ~13–15k mid-stream as the
  graph is largest) and ends **+18% total tokens vs B** — *despite generating 43% fewer CTEs*
  (68 vs 119). This is the paradox in its purest form: reuse cuts generation *count*, whole-graph
  injection inflates each *remaining* prompt more.
- **Selective injection fixes it.** S's per-question cost now **falls** over the stream
  (9.2k → 7.6k) and total tokens drop to **−8.4% vs baseline** and **−22.5% vs whole-graph S**,
  while **keeping the generation win** (74 vs 119 CTEs, −38% vs B) and **matching/beating accuracy**
  (77.5%). The graph no longer bloats the prompt, so reuse's generation savings finally show up in
  the token bottom line.

**Conclusion.** The token penalty was neither a small-sample artifact nor intrinsic to memory —
it was whole-graph prompt injection. With selective injection, the cold-start seed delivers
**fewer generations *and* fewer tokens *and* equal-or-better accuracy** on a long homogeneous
stream: the intended "same answers, cheaper."

---

## 5. Advanced retrieval: does ranking help at this scale? (honest null result)

Retrieval is staged: a typed **compatibility contract** (category + `outputs ⊇`, `grain ⊑`,
`filters =`) filters candidates, then a similarity **rank** picks one. We asked whether a more
advanced ranker beats the plain dense (embedding-cosine) one. We implemented (`retriever.py`):
- **hybrid** — fuse dense embeddings with **BM25** (lexical column/table tokens) via Reciprocal
  Rank Fusion, over the contract-filtered candidates (same accept gate, so only the *choice* among
  compatible views changes);
- **NSWIndex** — a from-scratch Navigable Small-World proximity graph (the graph that actually
  powers vector search). Its `recall@1` vs exact search is **1.00** over the seed views — at this
  scale it reproduces exact retrieval, so it is for the technique/scaling story, not quality.

Config S, `world_1`, 40-Q stream, `gen_topk=6`, dense vs hybrid retriever:

| metric | dense | hybrid (RRF: dense+BM25) |
|---|---|---|
| Execution accuracy | 75.0% | 75.0% |
| Exact reuse rate | 37.5% | 39.2% |
| Total CTE generations | 74 | 73 |
| Real total tokens | 341,795 | 339,857 |
| retrieval calls | 120 | 120 |
| retrievals with >1 compatible candidate | — | **16 (13%)** |
| fusion overturned the dense top-1 | — | **8** |

**Finding:** hybrid ≈ dense — identical accuracy, near-identical reuse/tokens (deltas are
`gpt-5-mini` nondeterminism). The intrinsic metric explains it: the contract leaves **>1 candidate
only 13% of the time**, so the ranker rarely has a decision to make; in the 16 cases it did, fusion
overturned the dense pick 8 times with **no downstream effect** (the LLM composer is robust to
which of several *compatible* views it gets). **Conclusion: at per-database library scale the typed
contract does the heavy lifting; the ranking algorithm (dense/hybrid/HNSW) is second-order.**
Advanced ranking (and ANN indexes) earn their keep only with large candidate pools — invest the
novelty budget in the contract, the cold-start seed, and (future) a learned/execution-grounded
retriever, not in fancier similarity ranking here.

---

## 6. Limitations & honest caveats

- **Tokens.** *Resolved* (§4): with whole-graph injection, memory reduces generation *count* but
  not *total tokens* (prompt bloat); with **selective (`--gen_topk`) injection**, S uses fewer
  tokens *and* fewer generations than baseline on a long stream. The default runs above used
  whole-graph injection (`gen_topk=0`); re-running them with `--gen_topk 6` is expected to remove
  the token penalty on the multi-DB sets too.
- **Determinism.** `gpt-5-mini` allows only default temperature (no temp=0), so configs see
  slightly different `propose_views` outputs run-to-run; small accuracy deltas are within noise.
- **Seed↔proposer vocabulary.** Reuse requires the seed to expose columns under the names the
  online proposer requests. We enforce exact-schema-name aliases + normalized matching; residual
  misses are genuine (the seed lacks that specific view).
- **Spider2 scope.** Only the local-SQLite subset is run; `bq*`/`sf*` tasks need cloud creds.
  Runs are scoped (few Q/DB) because each hard question costs ~25–30k tokens on `gpt-5-mini`.

---

## 6b. Guarding negative reuse: adversarial verifier + provenance memory

A bad *cache hit* — reusing a stored view that looks relevant but isn't (e.g. an all-rows view for
a completed-only question) — is the one way the view memory can hurt correctness. Beyond the
symbolic **compatibility guard**, we added two layers:

- **Layer 3 — adversarial verifier** (`agents.verify_reuse`, `--verify N`): after retrieval returns
  a hit, N skeptical verifier agents each look for a filter / grain / aggregation / time-window /
  output mismatch and default to REJECT if unsure; majority-allow to keep the reuse. Unit check: it
  REJECTs an all-rows view for a completed-only sub-goal and REUSEs it for a matching one.
- **Layer 4 — provenance memory** (`ViewSpec.validated_on` / `counter_examples`): each reused view
  learns its boundary from outcomes — a correct reuse is recorded, a negative reuse becomes a stored
  counter-example, and a later sub-goal embedding-similar to a counter-example is rejected pre-emptively.

Experiment (`world_1`, 30 Q; guard forced OFF to isolate the neural verifier):

| config | accuracy | reuse | neg-reuse | verifier-rejects | tokens |
|---|---|---|---|---|---|
| guard-on, no verify | 63.3% | 40.5% | 7 | 0 | 259k |
| guard-off, no verify | 70.0% | 31.1% | 5 | 0 | 271k |
| **guard-off, verify=3** | 66.7% | 27.8% | **2** | **5** | 332k |

**Reads:** the verifier is active (rejected 5 accepted reuses) and cut negative reuse to the lowest
of the three (2 vs 5 vs 7), at the cost of some reuse (27.8% vs 31.1%) and ~23% more tokens (3
verifier calls per hit); accuracy stays within noise. **Negative reuse is intrinsically rare here
(~2–4% of reuses), so run-to-run noise dominates the aggregate** — the verifier provably catches the
canonical bad case and lowered it in the run, but its net value scales with how often bad reuse
actually occurs (large when reuse is aggressive or the contract is weak; marginal when the symbolic
contract already filters well). Repro: `--verify 3` (optionally `--no_guard`).

---

## 7. Reproduce

```bash
# 1) build frozen cold-start seed graphs (no test questions)
python -m skiewsql.coldstart --dataset spider      --dbs world_1,dog_kennels,student_transcripts_tracking --tag seed
python -m skiewsql.coldstart --dataset spider2lite  --dbs bank_sales_trading,IPL,city_legislation           --tag seed

# 2) run the A / B / S comparison (S = cold-start seed). Add --gen_topk 6 for selective injection.
python -m skiewsql.realrun --dataset spider     --dbs world_1,dog_kennels,student_transcripts_tracking --limit 20 --configs A,B,S --seed_tag seed --tag exp1seed
python -m skiewsql.realrun --dataset spider2lite --dbs bank_sales_trading,IPL,city_legislation          --limit 5  --configs S,A,B --seed_tag seed --tag exp1seed

# 3) figures + markdown report
python -m skiewsql.analyze --tag exp1seed --dataset spider
python -m skiewsql.analyze --tag exp1seed --dataset spider2lite

# 4) long-stream token-curve experiment (B vs whole-graph S vs selective S)
python -m skiewsql.realrun --dataset spider --dbs world_1 --limit 40 --configs B,S --gen_topk 0 --seed_tag seed --tag longfull
python -m skiewsql.realrun --dataset spider --dbs world_1 --limit 40 --configs S   --gen_topk 6 --seed_tag seed --tag longsel
python -m skiewsql.plot_longstream        # -> results_real/longstream_token_curve.png

# 5) retriever comparison: dense vs hybrid (RRF dense+BM25)
python -m skiewsql.realrun --dataset spider --dbs world_1 --limit 40 --configs S --gen_topk 6 --retriever dense  --seed_tag seed --tag rdense
python -m skiewsql.realrun --dataset spider --dbs world_1 --limit 40 --configs S --gen_topk 6 --retriever hybrid --seed_tag seed --tag rhybrid
python -m skiewsql.compare_retrievers
```
