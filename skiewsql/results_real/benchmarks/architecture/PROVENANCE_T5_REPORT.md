# Provenance-aware AV-SQL N×1 graph benchmark with T=5

## Result in one paragraph

The implementation and both full database streams completed successfully. On the selected Spider stream, provenance-aware AV-SQL N×1 with graph reached **49/78, or 62.8%**. This is four more correct answers than the previous graph run with the same T=5 attempt limit, while using 24,614 fewer tokens. On the selected BIRD stream, it reached **55/129, or 42.6%**. This is three more correct answers than the previous graph run, but that older BIRD run used T=1, so it is not a controlled provenance comparison. The graph integrity result is strong. Every one of the 63 stored skills has contract v3 provenance, no stored skill is missing a provenance field, and neither final graph contains duplicate provenance signatures. The answer-quality evidence is promising on Spider but does not yet prove that graph reuse caused the gain. None of the seven Spider wins against the previous T=5 run used a stored skill.

## Experimental setting

| Setting | Value |
|---|---:|
| Architecture | AV-SQL N×1 with graph |
| Model | `gpt-5-mini` |
| Retrieval threshold | 0.6 |
| CTE generation and validation limit | T=5 |
| Value linking | Enabled |
| Graph initialization | Empty |
| Graph growth | Sequential, question by question |
| Spider stream | `student_transcripts_tracking`, 78 questions |
| BIRD stream | `european_football_2`, 129 questions |

T=5 follows the original AV-SQL maximum-attempt interpretation. A CTE is generated, checked by value retrieval, execution, and table-column selection consistency, then repaired and checked again only if needed. The process stops as soon as the CTE passes. It does not run five redundant checks after an already valid CTE.

## Current results

| Dataset stream | Correct | Accuracy | Tokens | LLM calls | Accepted generated CTEs | View-agent calls | Reuse selected | Reuse executed unchanged | Final graph |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Spider | 49/78 | 62.8% | 854,068 | 727 | 131 | 233 | 9 | 7 | 28 skills |
| BIRD | 55/129 | 42.6% | 2,624,044 | 1,310 | 333 | 511 | 5 | 4 | 35 skills |

The distinction between selected and executed unchanged matters. A selected skill can be removed or modified by final-query repair. Such a skill is not credited as an executed stored skill. For example, BIRD question `bird_dev_1136` selected `player_max_crossing`, but repair removed one stored output column. The final query still referenced a CTE with that name, yet it did not execute the stored skill unchanged.

## Normal Graph T=5 versus Provenance Graph T=5 on Spider

The previous `gpt5minifull_av_graph_avval_spider` run is the correct controlled comparison. It is the earlier Normal Graph T=5 run described in `REGISTRY_REPORT.md`. Both runs use graph-enabled AV-SQL N×1, value linking, the T=5 validation limit, the same model, the same database, and the same 78 questions. The main implementation difference is the new compact provenance used for retrieval verification, structural deduplication, and contribution diagnosis.

| Metric | Normal Graph T=5 | Provenance Graph T=5 | Change |
|---|---:|---:|---:|
| Correct | 45/78 | 49/78 | **+4** |
| Accuracy | 57.7% | 62.8% | **+5.1 percentage points** |
| Tokens | 878,682 | 854,068 | **-24,614, or -2.8%** |
| LLM calls | 759 | 727 | **-32** |
| View-generation tokens | 369,399 | 351,975 | **-17,424, or -4.7%** |
| View-generation calls | 244 | 233 | **-11** |
| Accepted generated CTEs | 124 | 131 | +7 |
| Reuse selected | 10 | 9 | -1 |
| Reuse executed unchanged | 8 | 7 | -1 |
| Final graph | 31 | 28 | -3 |
| Learning tokens | 94,410 | 91,244 | **-3,166** |
| Average seconds per question | 13.82 | 14.62 | +0.80 |

Therefore, provenance did **not** increase token use in the matched Spider experiment. It used 2.8% fewer total tokens and 4.7% fewer view-generation tokens. Most of the saving came from 11 fewer view-agent calls, 3 fewer revision calls, 3 fewer generated-test calls, and 1 fewer ablation generation call. The provenance verifier's candidate-choice stage used 4,623 more tokens, but the savings in the other stages were larger.

The provenance run admitted more accepted CTEs despite making fewer view-agent calls. This means a greater share of its attempts produced usable CTEs without another generation call. The slightly longer wall time does not follow the token count exactly because API latency, database checks, and local validation time vary independently of billed tokens.

The paired outcome is **7 wins, 3 losses, and 68 ties** for the new run. All ten flips are listed below. None selected or executed a graph skill in the new run, so these flips cannot be attributed directly to skill reuse.

| Direction | Question ID | Question |
|---|---|---|
| Win | `spider_dev_512` | What are the descriptions for all the math courses? |
| Win | `spider_dev_525` | What are the names and id of courses having at most 2 sections? |
| Win | `spider_dev_529` | What is the semester which most student registered in? Show both the name and the id. |
| Win | `spider_dev_536` | What are the first, middle, and last names for everybody enrolled in a Bachelors program? |
| Win | `spider_dev_550` | What are the last name of the students who live in North Carolina but have not registered in any degree programs? |
| Win | `spider_dev_557` | Who is the earliest graduate of the school? List the first name, middle name and last name. |
| Win | `spider_dev_567` | How many transcripts are released? |
| Loss | `spider_dev_570` | When was the last transcript released? |
| Loss | `spider_dev_575` | Find the semester when both Master students and Bachelor students got enrolled in. |
| Loss | `spider_dev_582` | What is the description for the section named h? |

Because the model is stochastic and each condition currently has one run, the four-answer net gain and the 2.8% token reduction are encouraging but not statistical conclusions. Multiple repeated runs with fixed sampling controls are needed to isolate the provenance change from model variance.

## Other historical comparisons

These rows are useful context, but they are not controlled provenance ablations because the old runs use T=1.

| Dataset | Historical baseline | Baseline result | Our provenance graph T=5 result | Accuracy change | Token change |
|---|---|---:|---:|---:|---:|
| Spider | Graph, T=1 | 41/78, 52.6% | 49/78, 62.8% | +10.3 points | +41.9% |
| Spider | No graph, T=1 | 47/78, 60.3% | 49/78, 62.8% | +2.6 points | +103.2% |
| BIRD | Graph, T=1 | 52/129, 40.3% | 55/129, 42.6% | +2.3 points | +35.8% |
| BIRD | No graph, T=1 | 51/129, 39.5% | 55/129, 42.6% | +3.1 points | +56.9% |

Every value in the fourth column is our main setting, which is provenance-aware AV-SQL N×1 with graph and T=5. The no-graph T=1 values appear only as historical baselines. We did not run a new provenance no-graph T=1 condition because provenance retrieval requires a graph.

The BIRD paired comparison against the older T=1 graph run has 14 wins, 11 losses, and 104 ties. Only one current BIRD win, `bird_dev_1123`, executed a stored skill. That question reused `players_with_max_potential` and was answered correctly. The ablation record was inconclusive rather than a demonstrated causal win.

## Reuse outcomes

| Dataset | Selected questions correct | Executed unchanged correct | Incorrect selected reuse | Causal wins | Causal losses |
|---|---:|---:|---:|---:|---:|
| Spider | 6/9 | 4/7 | 3 | 0 | 0 |
| BIRD | 1/5 | 1/4 | 4 | 0 | 0 |

### Spider selected skills

| Question | Skill | Executed unchanged | Correct |
|---|---|---:|---:|
| `spider_dev_516` | `department_degree_counts` | Yes | Yes |
| `spider_dev_517` | `department_degree_counts` | Yes | Yes |
| `spider_dev_518` | `department_degree_counts` | Yes | Yes |
| `spider_dev_521` | `department_degree_counts` | No | Yes |
| `spider_dev_522` | `department_degree_counts` | No | Yes |
| `spider_dev_526` | `course_section_counts` | Yes | No |
| `spider_dev_534` | `student_semester_degree_program_counts` | Yes | No |
| `spider_dev_572` | `student_course_transcript_counts` | Yes | Yes |
| `spider_dev_578` | `students_per_current_address` | Yes | No |

### BIRD selected skills

| Question | Skill | Executed unchanged | Correct |
|---|---|---:|---:|
| `bird_dev_1079` | `player_max_height` | Yes | No |
| `bird_dev_1086` | `player_avg_heading_accuracy_by_player_fifa_id` | Yes | No |
| `bird_dev_1123` | `players_with_max_potential` | Yes | Yes |
| `bird_dev_1135` | `player_min_potential` | Yes | No |
| `bird_dev_1136` | `player_max_crossing` | No, modified by repair | No |

This is the main unresolved result. Provenance storage and structural deduplication work, but retrieval precision remains weak, especially on BIRD. The final LLM can sometimes ignore or repair a poor reuse, but it did not reliably rescue these cases.

## Provenance and graph integrity

| Check | Spider | BIRD |
|---|---:|---:|
| Stored skills | 28 | 35 |
| Contract v3 skills | 28/28 | 35/35 |
| Skills with all five compact provenance fields | 28/28 | 35/35 |
| Duplicate provenance-signature groups | 0 | 0 |
| Duplicate admissions merged | 6 | 4 |
| Result-equivalent admissions merged | 1 | 1 |

The five required compact fields are `source_columns`, `output_lineage`, `operators`, `upstream_skills`, and `parameter_bindings`. The Spider pilot exposed two versions of `department_degree_counts` whose join equality was written in opposite directions. Join-key canonicalization now treats those structures as equivalent. The final Spider graph contains only one `department_degree_counts` node.

The new contribution records also show how each referenced skill feeds the final query. For example, `department_degree_counts` contributed `department_name`, `department_id`, and `degree_count` through projection, ordering, filtering, and aggregation roles. This information is kept in execution episodes, not as large tuple-level provenance inside the graph.

## What the experiment proves and does not prove

The experiment demonstrates that compact provenance can be derived, persisted, exposed to retrieval verification, used in structural deduplication, and used for final-query contribution diagnosis without breaking the runner. It also demonstrates a clean graph with no structurally duplicate skills in these two streams.

The experiment does not yet demonstrate that provenance-aware retrieval improves final SQL accuracy. AV-SQL N×1 sends holistic requests with empty required output and grain contracts. Therefore the strongest deterministic qualified-column lineage rejection usually has no requested qualified column to check. No retrieval candidate in these runs was rejected specifically by that hard provenance rule. Provenance still affected stored contracts, structural equivalence, verifier context, and diagnostics, but dependency-style requests with explicit outputs and grain are the more direct test of provenance compatibility.

The result also does not demonstrate a graph-reuse accuracy win. There were no recorded causal wins after regeneration ablation. The one correct BIRD reuse and the four correct unchanged Spider reuses are successful executions, but the current ablations did not establish that those answers would have failed without the stored skills.

## Verification

The repository test suite passes **65/65 tests**. Python compilation and `git diff --check` also pass. Added tests cover provenance extraction, qualified-output lineage rejection, provenance-aware equivalence, reversed join-key canonicalization, and final-query contribution tracing.

## Artifacts

- [Spider full results](runs/registry_provenance_t5/provenance_t5_av_graph_spider_A_SkiewSQL.json)
- [Spider summary](runs/registry_provenance_t5/provenance_t5_av_graph_spider_summary.json)
- [Spider graph](graphs/registry_provenance_t5/provenance_t5_av_graph_spider_A_SkiewSQL/student_transcripts_tracking.json)
- [Spider graph markdown](graphs/registry_provenance_t5/provenance_t5_av_graph_spider_A_SkiewSQL/student_transcripts_tracking.md)
- [Spider execution episodes](graphs/registry_provenance_t5/provenance_t5_av_graph_spider_A_SkiewSQL/student_transcripts_tracking.episodes.jsonl)
- [BIRD full results](runs/registry_provenance_t5/provenance_t5_av_graph_bird_A_SkiewSQL.json)
- [BIRD summary](runs/registry_provenance_t5/provenance_t5_av_graph_bird_summary.json)
- [BIRD graph](graphs/registry_provenance_t5/provenance_t5_av_graph_bird_A_SkiewSQL/european_football_2.json)
- [BIRD graph markdown](graphs/registry_provenance_t5/provenance_t5_av_graph_bird_A_SkiewSQL/european_football_2.md)
- [BIRD execution episodes](graphs/registry_provenance_t5/provenance_t5_av_graph_bird_A_SkiewSQL/european_football_2.episodes.jsonl)
