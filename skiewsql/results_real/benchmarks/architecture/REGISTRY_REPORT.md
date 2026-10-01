# Skill-registry rerun of the semantic20 benchmark

> Run on 30 September 2026. This compares the skill-registry pipeline (`realrun.py --skill_registry 1`, now the default) with the earlier semantic20 runs in [REPORT.md](REPORT.md). The earlier artifacts are untouched. The new ones use the tag `registry20_*`.

## Bottom line

The registry removes the failure that dominated the earlier BIRD run: **negative reuse drops from 13 to 0**, and adaptive recovers `bird_dev_1038` without losing any other question. Overall accuracy is 21/60, against 20/60 before. That difference is within run-to-run noise: the no-graph arm, whose code is effectively unchanged, moved by ±2 per dataset between the two runs.

The registry does **not yet save anything through reuse**. It admitted 6 skills, and not one was reused. On BIRD the graph stays empty, because the final SQL almost never reads the AV chunk views, so there is nothing legitimate to credit or promote. Without the unsafe reuse, adaptive generates more CTEs and uses more tokens: its token saving against no-graph falls from 22.2% to 8.5%.

## Setup

Identical to REPORT.md: local Ollama `gemma3:4b` at temperature 0, 20 questions each from Spider `student_transcripts_tracking`, BIRD `european_football_2`, and Spider2-lite `bank_sales_trading` + `education_business`. The settings are 1,000-token chunks, at most 3 subgoals, 1 view attempt, 1 repair, 1 self-consistency pass, no value linking, and τ = 0.6. Only two arms were rerun: AV-SQL without a graph (`nx1`, config B) and adaptive with a graph (`auto`, config A). The registry defaults were on: Stage-5 verifier, ablation, generated tests, and final-SQL promotion.

Between the first pass and this report, a lineage bug was fixed (see below). Only the Spider2-lite adaptive run admitted skills, so only that run was repeated.

## Accuracy

| Method | Run | Spider | BIRD | Spider2-lite | Overall |
|---|---|---:|---:|---:|---:|
| AV-SQL, no graph | before | 13/20 | 7/20 | 0/20 | 20/60 |
| AV-SQL, no graph | registry | 15/20 | 5/20 | 0/20 | 20/60 |
| Adaptive + graph | before | 17/20 | 3/20 | 0/20 | 20/60 |
| Adaptive + graph | registry | 17/20 | 4/20 | 0/20 | 21/60 |

Paired, per question:

- **Adaptive, registry vs before:** Spider 0 wins / 0 losses. BIRD 1/0 (`bird_dev_1038` recovered). Spider2-lite 0/0.
- **Adaptive vs no-graph, both from the registry run:** Spider 4/2. BIRD 2/3. Spider2-lite 0/0. Spider still gains from the easy-route bypass. BIRD is still slightly negative, but no longer because of reuse (see below).
- **No-graph, registry vs before (the noise floor):** Spider 3/1. BIRD 1/3. This arm's code changed only in CTE ordering, so these flips are model nondeterminism.

## Cost and reuse

| Dataset | Method | Run | Tokens (of which learning) | Calls | CTEs generated | Reuse questions | Negative reuse | Align calls | Admitted |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Spider | Adaptive | before | 37,024 | 68 | 1 | 1 | 0 | 0 | — |
| Spider | Adaptive | registry | 49,281 (8,982) | 88 | 2 | 0 | 0 | 0 | 0 |
| BIRD | Adaptive | before | 246,038 | 104 | 2 | 16 | **13** | 0 | — |
| BIRD | Adaptive | registry | 351,967 (9,337) | 150 | 31 | 0 | **0** | 0 | 0 |
| Spider2-lite | Adaptive | before | 421,181 | 294 | 16 | 2 | 2 | 144 | — |
| Spider2-lite | Adaptive | registry | 440,777 (12,450) | 323 | 30 | 0 | 0 | 138 | 6 |
| All | No graph | registry | 920,212 | 379 | 101 | 0 | 0 | 0 | — |

Pooled adaptive tokens: 704,243 before and 842,025 now, against 904,664 and 920,212 for no-graph. The saving falls from 22.2% to 8.5%.

## Why nothing was reused

**1. The final SQL rarely reads the views.** This counts questions whose outer query reads at least one CTE, among questions that built or reused views:

| Run | Method | Spider | BIRD | Spider2-lite |
|---|---|---:|---:|---:|
| before | AV-SQL, no graph | 5/20 | 2/20 | 13/16 |
| before | Adaptive | 0/2 | 0/17 | 9/12 |
| registry | AV-SQL, no graph | 5/20 | 0/18 | 10/19 |
| registry | Adaptive | 0/2 | 1/16 | 10/14 |

On BIRD, `gemma3:4b` writes the answer against base tables and leaves the chunk views dead in the `WITH` clause. The execution repair also often rewrites the query without them (for example, `bird_dev_1025`). This confirms the earlier REPORT's reading: the old BIRD "reuse hits" never contributed rows. They did harm by replacing fresh exploration. Under credit assignment, a dead view earns nothing and is not promoted. Of 63 views created across the adaptive runs, 54 were discarded as unreferenced or modified by repair, 3 were rejected for unknown grain, and 6 were admitted.

**2. The admitted skills did not match later requests.** All 6 admitted skills came from Spider2-lite `bank_sales_trading`, which uses the dependency route. Its 43 later requests produced no hit. The reasons: 46 Stage-2 rejections for "required outputs not exposed", where the decomposer asks for logical names like `net_balance` that differ from stored columns like `balance`; 24 Stage-1 rejections for tables outside the request's chunk domain; and a few rejections for filter scope, aggregation, or similarity below τ. With no hits, searching before alignment saved nothing (138 alignment calls against 144).

## Learning overhead

Post-answer learning used 30,769 tokens in total, 3.7% of the adaptive arm's tokens. Most of it was `extract_final`: 45 calls and 26,810 tokens, which admitted **zero** relations. The remaining learning calls were 6 generated-test calls. There were no ablation or description calls, because no reused skill executed and no AV view was promoted.

## Bug found and fixed during this run

When a promoted view read only another view, `contracts.derive` fell back to the generator's self-reported `source_tables`, which named the dependency view. The view name then entered the skill's lineage with a blank fingerprint. Every skill built on another skill looked like it had a "schema changed" table and was never eligible. The first Spider2-lite pass showed 34 such rejections. The SQL is now authoritative even when it has no base tables, and lineage never includes view names (regression test `test_view_over_a_view_has_base_table_lineage_only`). After the fix, all 6 skills have `customer_transactions` as their lineage.

## Conclusions

1. **Safety works.** No negative reuse, no dead-view credit, and the BIRD failure from REPORT.md no longer occurs.
2. **Reuse savings need two more things:** (a) a composer that actually reads the views, which may require a stronger model than `gemma3:4b`; and (b) matching between the decomposer's logical output names and stored column names in Stage 2. Output naming is now the main reason for misses.
3. **Final-SQL extraction is not paying off here.** Consider skipping it on the easy direct-SQL route (`--promote_final 0`) until a stronger model produces extractable relations.
4. **Sample size limits every accuracy claim.** With ±2 noise per 20-question dataset, confirming any accuracy effect needs more questions, more databases, or repeated runs.

## Reproduction

```bash
bash skiewsql/results_real/benchmarks/architecture/run_registry_benchmark.sh
python skiewsql/results_real/benchmarks/architecture/analyze_registry_benchmark.py
```

Raw rows are under `runs/registry/`, and the machine-readable comparison is `runs/registry/REGISTRY_SUMMARY.json` (all tables: `runs/registry/registry_tables.md`). Grown graphs, together with each database's `*.episodes.jsonl` and `*.ledger.jsonl`, are under `graphs/registry/`. Logs are under `logs/registry/`.

---

# Rerun after the review fixes (1 October 2026)

This run uses the same benchmark with all eight review fixes applied: prefetch grounding, effective (inherited) filters, a multigraph, verifier confidence and votes, conservative constant rejection, data fingerprints, index-based candidates, and episode persistence. The tag is `registryfix20_*`, under `runs/registry_fix/`. The first two runs are unchanged.

## Accuracy

| Method | Run | Spider | BIRD | Spider2-lite | Overall |
|---|---|---:|---:|---:|---:|
| AV-SQL, no graph | before | 13/20 | 7/20 | 0/20 | 20/60 |
| AV-SQL, no graph | registry | 15/20 | 5/20 | 0/20 | 20/60 |
| AV-SQL, no graph | fixed | 17/20 | 3/20 | 1/20 | 21/60 |
| Adaptive + graph | before | 17/20 | 3/20 | 0/20 | 20/60 |
| Adaptive + graph | registry | 17/20 | 4/20 | 0/20 | 21/60 |
| Adaptive + graph | fixed | 17/20 | 3/20 | 0/20 | 20/60 |

Across three runs, the no-graph arm ranged from 13 to 17 on Spider and from 3 to 7 on BIRD, although its code barely changed. Adaptive's differences between runs (BIRD 3 → 4 → 3) are inside that range, and so is its paired comparison with the fixed-run no-graph arm (Spider 1/1, BIRD 1/1, Spider2-lite 0/1). **On 20 questions per dataset, none of the three pipelines is distinguishable in accuracy.**

## Cost and reuse (adaptive)

| Dataset | Run | Tokens (learning) | Calls | CTEs | Reuse questions | Negative reuse | Align calls | Admitted |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Spider | before | 37,024 | 68 | 1 | 1 | 0 | 0 | — |
| Spider | registry | 49,281 (8,982) | 88 | 2 | 0 | 0 | 0 | 0 |
| Spider | fixed | 47,952 (11,674) | 89 | 2 | 0 | 0 | 0 | 1 |
| BIRD | before | 246,038 | 104 | 2 | 16 | 13 | 0 | — |
| BIRD | registry | 351,967 (9,337) | 150 | 31 | 0 | 0 | 0 | 0 |
| BIRD | fixed | 365,792 (13,439) | 158 | 37 | 0 | 0 | 0 | 0 |
| Spider2-lite | before | 421,181 | 294 | 16 | 2 | 2 | 144 | — |
| Spider2-lite | registry | 440,777 (12,450) | 323 | 30 | 0 | 0 | 138 | 6 |
| Spider2-lite | fixed | 446,346 (9,362) | 323 | 26 | 0 | 0 | 144 | 2 |

Pooled adaptive tokens are 860,090, against 898,394 for no-graph in the same run: a 4.3% saving, compared with 8.5% in the registry run and 22.2% before.

## Why there is still no reuse

- **Almost nothing is admitted.** Of 65 new views, 58 were discarded because the final SQL did not read them unmodified, 4 were rejected (incomplete contract or a failed test), and 3 were admitted. The final SQL reads the views in only 1 of 16 BIRD questions and 3 of 20 Spider no-graph questions, but in 12 of 15 Spider2-lite adaptive questions. The final-SQL extraction made 48 calls and admitted nothing.
- **Nothing matches.** Of 112 registry lookups, 109 produced no index candidate: the graph was empty (BIRD), or no stored skill exposed the requested output names. The remaining 3 failed Stage 2 or 3. No prefetch hit occurred, so the grounding step (fix 1) never fired. With no hits, alignment on Spider2-lite stays at the full 144 calls.
- The fixes make the registry **stricter**: index candidates require every output name, and inherited filters narrow the matches. With this model's naming variability, that turns near misses into no candidates at all. This is the intended safe-miss direction, but it means the benchmark currently cannot exercise reuse.

## Conclusion

The fixed pipeline is safe (0 negative reuse, 0 errors) and costs about the same as the first registry run. On this benchmark it neither helps nor hurts accuracy measurably, and it saves nothing through reuse, because with `gemma3:4b` (a) the final queries rarely read the views and (b) decomposer output names rarely match stored columns. Showing reuse benefits requires a stronger model or output-name normalization in Stage 0 and Stage 2, plus more questions per database.

---

# Rerun with gpt-5-mini (OpenAI, 1 October 2026)

This run uses the same code as the "fixed" run, the same 60 questions, and the same settings. Only the model differs: `gpt-5-mini` through the OpenAI API, with `text-embedding-3-small` embeddings. The tag is `gpt5mini20_*`, under `runs/registry_gpt5mini/`.

## Accuracy

| Method | Model | Spider | BIRD | Spider2-lite | Overall |
|---|---|---:|---:|---:|---:|
| AV-SQL, no graph | gemma3:4b (fixed run) | 17/20 | 3/20 | 1/20 | 21/60 |
| Adaptive + registry | gemma3:4b (fixed run) | 17/20 | 3/20 | 0/20 | 20/60 |
| AV-SQL, no graph | gpt-5-mini | 17/20 | 6/20 | 2/20 | **25/60** |
| Adaptive + registry | gpt-5-mini | 17/20 | 4/20 | 0/20 | 21/60 |

Paired, gpt-5-mini adaptive vs gpt-5-mini no-graph: Spider 0/0, BIRD 1/3 (losses `bird_dev_1020`, `1037`, `1038`), Spider2-lite 0/2 (losses `local300`, `local301`). With the stronger model, **no-graph is ahead by 4 questions**, which is the largest gap in any run so far. It remains close to the ±2-per-dataset noise, though. The gap does not come from reuse: no loss involved a reused skill. Two losses (`bird_dev_1020`, `1038`) went to direct SQL: with gpt-5-mini, adaptive routed 16 of 20 BIRD questions there (gemma: 4). The other three (`bird_dev_1037`, `local300`, `local301`) went to dependency N×M, where AV-SQL's per-chunk exploration answered them and the decomposition did not.

## Cost and reuse

| Dataset | Method | Tokens (learning) | Calls | CTEs | Executed reuses | Align calls | Admitted |
|---|---|---:|---:|---:|---:|---:|---:|
| Spider | no graph | 123,061 | 97 | 23 | — | 0 | — |
| Spider | adaptive | 44,354 (13,441) | 95 | 0 | 1 | 0 | 2 |
| BIRD | no graph | 259,467 | 113 | 15 | — | 0 | — |
| BIRD | adaptive | 172,492 (44,022) | 154 | 12 | 0 | 36 | 18 |
| Spider2-lite | no graph | 290,015 | 129 | 33 | — | 0 | — |
| Spider2-lite | adaptive | 407,791 (49,237) | 336 | 41 | 0 | 144 | 16 |

Pooled tokens: adaptive 624,637 against 672,543 for no-graph, a 7.1% saving. Learning accounts for 106,700 tokens (17% of adaptive), mostly `gen_tests` (40 calls) and `extract_final` (57 calls).

## What changed with the stronger model

- **The final SQL uses the views.** Every adaptive question that built views had a final query reading them (Spider 1/1, BIRD 4/4, Spider2-lite 16/16). With gemma this was 1/16 on BIRD.
- **The registry grows.** 36 skills were admitted (gemma: 3): 23 generated views and 13 relations extracted from final SQL. A further 23 views and 24 extractions were rejected (incomplete contract, a failed test, or kept question constants), and 4 were merged as duplicates or equivalents.
- **First real reuse, but only one.** `spider_dev_518` reused `department_degree_counts` exactly, with a single verifier vote. The final SQL executed it unmodified and the answer was correct. Ablation was inconclusive, because the regenerated view did not keep the interface, so credit fell back to association (positive).
- **Matching is now the bottleneck.** Of 70 registry lookups, 63 found no index candidate: no stored skill exposed every requested output name in the requested category. Of the rest, 4 failed the table-domain check, 7 fell below τ, and 1 was reused. BIRD had only 4 hard or moderate questions, so the 18 BIRD skills were offered to just 12 lookups.

## Conclusion

A stronger model resolves the first blocker (views are used and admitted) but not the second. Output-name matching still prevents almost all reuse. On these 20-question samples, the registry pipeline costs about 7% fewer tokens than no-graph and is 4 questions less accurate. The accuracy difference comes from routing and decomposition, not reuse. The next experiment should add output-name normalization at candidate generation (for example, embedding or LLM mapping of logical outputs to stored columns before the index lookup), and use more questions per database, so the registry sees repeated needs.

---

# Full-database run with output-name mapping (gpt-5-mini, 1 October 2026)

Two changes from the previous gpt-5-mini run:

1. **Stage 0 name mapping.** Before the index lookup, each requested output and grain key without an exact stored match is mapped to the closest column name used by stored skills of the same category, by shared word tokens (Jaccard ≥ 0.5) or embeddings (≥ 0.6 for outputs, ≥ 0.8 for grain keys). Any match that relies on a mapping must pass the LLM verifier, which is told the renames.
2. **Every question of each database**: Spider `student_transcripts_tracking` 78, BIRD `european_football_2` 129, and Spider2-lite 20 (already all of them). That is 227 questions per arm, so later questions can reuse what earlier ones built.

The tag is `gpt5minifull_*`, under `runs/registry_gpt5mini_full/`. Both arms ran in parallel with no errors and no failed learning steps.

## Accuracy

| Method | Spider | BIRD | Spider2-lite | Overall |
|---|---:|---:|---:|---:|
| AV-SQL, no graph | 47/78 | 51/129 | 3/20 | **101/227 (44.5%)** |
| Adaptive + registry | 41/78 | 49/129 | 1/20 | 91/227 (40.1%) |

Paired, adaptive vs no-graph: Spider 1 win / 7 losses, BIRD 12/14, Spider2-lite 0/2, for **13 wins and 23 losses overall**. This is the first sample large enough for the gap to stand out from noise, and it favours no-graph.

The gap comes from routing, not reuse. On the same questions, by adaptive route:

| Adaptive route | Questions | Adaptive correct | No-graph correct |
|---|---:|---:|---:|
| Easy → direct SQL | 169 | 79 | 83 |
| Moderate → AV N×1 + registry | 22 | 7 | 10 |
| Hard → dependency N×M + registry | 36 | 5 | 8 |

AV-SQL's per-chunk exploration is slightly better on every route, including the 169 questions adaptive answered with direct SQL. Neither executed reuse caused a loss (see below).

## Cost

| | Adaptive + registry | No graph |
|---|---:|---:|
| Tokens | 1,523,342 | 2,384,531 |
| of which learning | 255,394 (16.8%) | — |
| LLM calls | 1,876 | 1,209 |

Adaptive uses **36% fewer tokens** but 55% more calls (routing, alignment, and learning add many short calls). The saving comes from direct SQL on easy questions. Learning is dominated by `extract_final` (221 calls) and `gen_tests` (86 calls).

## Reuse

- The registry grew to 78 skills (Spider 33, BIRD 24, Spider2-lite 21).
- 159 lookups: 52 had index candidates, 3 reached the verifier, and **2 reuses executed**. Both came in the second half of the Spider stream:
  - `spider_dev_550` (hard route) reused `student_degree_registrations`. The question was wrong under both arms. Ablation was neutral, so the skill was not blamed.
  - `spider_dev_572` (moderate route) reused `student_course_transcript_counts`. It was correct under both arms. Ablation was inconclusive, so the credit is association only.
- **Name mapping fired on 50 lookups and produced 0 candidates.** The mapped requests still asked for relations no stored skill provides. A typical case wanted `total_quantity_2021` per `(division_id, product_id)`, while the closest stored skill held unique-product counts per `(product_segment, year)`. Some proposed renames were wrong (`region_id` → `division_id`), but the full-coverage index lookup and the grain check stopped all of them before reuse. So mapping added no false hits and found no real ones.
- The most common rejections were tables outside the request's chunk domain (290, from moderate per-chunk requests), stored views narrower than requested (15), and similarity below τ (most of the rest).

## Conclusion

With the stronger model and full databases, the registry is safe (no harmful reuse, no execution errors) and grows normally. But questions within one database rarely need the same intermediate relation: 78 skills produced 2 reuses in 227 questions, and neither affected correctness. Adaptive's 36% token saving comes from easy-question routing, not from the graph. It costs 10 questions (4.4 points) against AV-SQL without a graph, spread across all three routes.

For the thesis claim this means that, on these benchmarks, reuse of intermediate relations is limited by **how often needs actually repeat**, not by retrieval mechanics. Stronger evidence for reuse would need a workload with repeated analytical needs (for example SQLFlow-style paraphrase or variant streams, or several questions per business metric), or reuse at a coarser level, such as skills shared across the moderate route's chunk exploration.

## Follow-up: Spider2-lite with AV-SQL N×1 plus the registry (no routing)

Same model, same 20 questions, same settings. Config A (graph and registry) runs every question through AV-SQL N×1, with no difficulty routing and no dependency N×M. The tag is `gpt5minifull_av_graph`.

| Setup | Correct | Tokens (learning) | Calls | CTEs | Reuse | Skills admitted |
|---|---:|---:|---:|---:|---:|---:|
| No graph, AV-SQL N×1 | 3/20 | 291,690 | 131 | 38 | — | — |
| Graph + registry, AV-SQL N×1 only | **5/20** | 342,093 (32,979) | 175 | 26 | 0 | 6 |
| Adaptive (19 N×M, 1 direct) | 1/20 | 436,110 (56,350) | 512 | 37 | 0 | 21 |

N×1 with the registry gets every question no-graph got (`local058`, `local059`, `local163`) plus `local284` and `local253`, with no losses. **No reuse occurred**: the 6 admitted skills were never retrieved. The answer path is therefore the same as no-graph, and the 2 extra answers are run-to-run variation of gpt-5-mini, not a registry effect. The cost difference (+50k tokens, of which 33k learning) is the registry's overhead with nothing to reuse.

What this run does show is that routing Spider2-lite's questions to dependency N×M is what hurt adaptive: 1/20 with 171 alignment calls, against 3–5/20 for AV-SQL N×1 on the same questions.

## Follow-up: graph + registry with AV-SQL N×1 on all three datasets

Same model (gpt-5-mini), all 227 questions, config A with `--architecture nx1`. Every question goes through AV-SQL N×1 with registry retrieval, with no difficulty routing. The tag is `gpt5minifull_av_graph`.

| Dataset | No graph, N×1 | Graph + registry, N×1 | Adaptive |
|---|---:|---:|---:|
| Spider (78) | **47** | 41 | 41 |
| BIRD (129) | 51 | **52** | 49 |
| Spider2-lite (20) | 3 | **5** | 1 |
| **Total (227)** | **101 (44.5%)** | 98 (43.2%) | 91 (40.1%) |
| Paired W/L vs no graph | — | 13 / 16 | 13 / 23 |
| Tokens | 2,384,531 | 2,876,414 | 1,523,342 |
| of which learning | — | 287,713 | 255,394 |
| LLM calls | 1,209 | 1,895 | 1,876 |
| Questions with reuse | — | 15 | 2 |

**Accuracy.** Graph + registry N×1 is within noise of no-graph: 98 vs 101, with 13 paired wins and 16 losses. Unlike adaptive (13/23), it shows no systematic deficit. Removing difficulty routing removes most of adaptive's loss.

**This is the most reuse in any run so far.** 15 questions reused a stored skill (Spider 11, BIRD 4), all exact reuses of promoted AV chunk views, and the final SQL executed every one. Reuse is accuracy-neutral: the reuse questions scored 9/15, against 9/15 for no-graph on the same questions (Spider 7 vs 8, BIRD 2 vs 1). Spider's 6-question deficit is on the 67 questions **without** reuse (34 vs 39), so it is run-to-run variation, not harm from reuse. On Spider2-lite and most of BIRD nothing matched, so those answers are effectively no-graph.

**Ablation does not work for AV chunk views.** All 15 ablations were inconclusive: the regenerated exploratory view never kept the reused view's columns, so the final SELECT could not run on it. Skill credit therefore fell back to association: 9 positive outcomes and 6 negative.

**It costs more, not less.** Graph + registry N×1 uses 21% more tokens and 57% more calls than no-graph. Learning alone (final-SQL extraction, generated tests, promotion) is 288k tokens, and 15 reuses do not save enough generation to offset it.

**Bottom line across all runs.** AV-SQL N×1 is the strongest base path on these benchmarks. Adding the registry to it is accuracy-neutral and safe, but adds about 21% cost, because analytical needs repeat too rarely within one database (15 reuses in 227 questions at best). Adaptive's token saving comes from its easy route, but its routing, especially sending questions to dependency N×M, costs about 4 accuracy points.

## Follow-up: planner review loop (per-question reasons + reject-and-regenerate)

Graph + registry N×1 with the planner review loop: every view carries a per-question reason, and the planner may reject any view, which is then regenerated with AV-SQL N×1. Rounds were **unlimited** in this run (the default is now 2). gpt-5-mini, Spider + BIRD, tag `gpt5minifull_av_graph_review`.

| Setup (Spider 78 + BIRD 129) | Correct | Tokens | Calls | Paired W/L vs no graph | Reuse questions (correct / no-graph correct) | Rejections |
|---|---:|---:|---:|---:|---:|---:|
| No graph N×1 | **98 (47.3%)** | 2.09M | 1,078 | — | — | — |
| Graph N×1 | 93 (44.9%) | 2.53M | 1,720 | 11 / 16 | 15 (9 / 9) | — |
| Graph N×1 + review | 95 (45.9%) | **4.25M** | 2,406 | 11 / 14 | 13 (10 / 9) | 471 |

Per dataset: Spider 47 / 41 / 43, BIRD 51 / 52 / 52.

- **Accuracy:** +2 over graph N×1 without review, still 3 below no-graph. Both differences are within noise.
- **Reuse questions:** 10 of 13 correct, against 9 for no-graph on the same questions.
- **The planner rejects freely:** 471 rejections. Spider: 118 in 41 of 78 questions. BIRD: 353 in 85 of 129 questions, with 34 BIRD questions needing more than 2 rounds and one reaching 26. Most rejections hit freshly generated chunk views. Only 4 stored skills received negative evidence (2 Spider, 2 BIRD).
- **Cost:** 4.25M tokens, 2× no-graph and +68% over graph N×1. On BIRD alone, 3.39M against 1.93M.

**Change made after this run:** `--max_review_rounds` now defaults to **2** (0 = unlimited) to bound the cost.
