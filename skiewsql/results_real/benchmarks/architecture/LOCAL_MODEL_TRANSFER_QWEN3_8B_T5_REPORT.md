# Cross-model skill-memory transfer with Qwen3 8B

## Bottom line

The full Spider and BIRD experiment completed successfully. A local `qwen3:8b` model was evaluated with AV-SQL N×1 and T=5 under two conditions. The first condition had no cross-question graph memory. The second loaded the previously learned GPT provenance registry as a warm start and allowed it to evolve into a separately saved Qwen registry.

The warm-start condition improved Spider from **42/78 to 47/78**, but declined on BIRD from **49/129 to 48/129**. Pooled accuracy increased from **91/207, or 44.0%**, to **95/207, or 45.9%**. This cost 24.2% more tokens and 49.2% more LLM calls. Only one seed skill was reused across all 207 questions, and its regeneration ablation was inconclusive. The experiment therefore does not demonstrate efficient cross-model skill reuse. It demonstrates that Qwen usually abstains from using GPT-generated skills and that the presence of the registry changes generation behavior even when no skill is selected.

## Experimental setting

| Setting | Value |
|---|---|
| Chat model | Local Ollama `qwen3:8b` |
| Hardware | NVIDIA RTX 4090 |
| Thinking mode | Disabled |
| Temperature | 0 |
| Context | 16,384 tokens |
| Embeddings | `nomic-embed-text:latest` |
| Architecture | AV-SQL N×1 |
| View validation | T=5 maximum attempts |
| Final SQL repair | Up to 5 attempts |
| Value linking | Enabled |
| Retrieval threshold | 0.6 |
| Spider stream | `student_transcripts_tracking`, 78 questions |
| BIRD stream | `european_football_2`, 129 questions |
| Spider seed | 28 GPT-generated provenance skills |
| BIRD seed | 35 GPT-generated provenance skills |
| Memory behavior | Read-write copy of seed, saved separately |

The no-graph and warm-start conditions use the same local model, question order, schemas, and T=5 settings. The seed graphs are the outputs of the earlier GPT provenance experiment. The original seed files were loaded but never overwritten.

## Main results

| Dataset | Condition | Correct | Accuracy | Tokens | Calls | Generated CTEs | Seed reuse | Verifier rejections |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Spider | No graph | 42/78 | 53.8% | 1,598,854 | 800 | 57 | 0 | 0 |
| Spider | Warm start | **47/78** | **60.3%** | 2,074,691 | 1,268 | 58 | 1 | 104 |
| BIRD | No graph | **49/129** | **38.0%** | 5,476,921 | 2,042 | 86 | 0 | 0 |
| BIRD | Warm start | 48/129 | 37.2% | 6,711,861 | 2,971 | 74 | 0 | 232 |
| Pooled | No graph | 91/207 | 44.0% | 7,075,775 | 2,842 | 143 | 0 | 0 |
| Pooled | Warm start | **95/207** | **45.9%** | 8,786,552 | 4,239 | 132 | 1 | 336 |

Pooled warm-start cost increased by **1,710,777 tokens, or 24.2%**, and **1,397 calls, or 49.2%**. The net accuracy change was four additional correct answers, or 1.9 percentage points.

## Paired question outcomes

| Dataset | Warm-start wins | Warm-start losses | Ties | Net change |
|---|---:|---:|---:|---:|
| Spider | 7 | 2 | 69 | +5 |
| BIRD | 11 | 12 | 106 | -1 |
| Pooled | 18 | 14 | 175 | +4 |

### Spider wins

| Question ID | Question | Reused a seed skill |
|---|---|---:|
| `spider_dev_512` | What are the descriptions for all the math courses? | No |
| `spider_dev_546` | What are the names of all courses that have some students enrolled? | No |
| `spider_dev_551` | Show the date and id of the transcript with at least 2 course results. | No |
| `spider_dev_566` | What is the earliest date of a transcript release, and what details can you tell me? | No |
| `spider_dev_567` | How many transcripts are released? | No |
| `spider_dev_571` | How many times at most can a course enrollment result show in different transcripts? Also show the course enrollment id. | **Yes** |
| `spider_dev_580` | What other details can you tell me about students in reverse alphabetical order? | No |

### Spider losses

| Question ID | Question | Reused a seed skill |
|---|---|---:|
| `spider_dev_507` | What are all the addresses including line 1 and line 2? | No |
| `spider_dev_573` | Show the date of the transcript which shows the least number of results, also list the id. | No |

Only one of the seven Spider wins directly reused a transferred skill. The other six wins and both losses resulted from different generations or final compositions. This means the five-answer Spider improvement cannot be attributed to skill reuse alone.

### BIRD flips

The warm-start condition had 11 wins and 12 losses on BIRD. None selected or executed a seed skill. These 23 flips are therefore generation differences, not reuse outcomes.

Warm-start wins occurred on `bird_dev_1020`, `bird_dev_1025`, `bird_dev_1033`, `bird_dev_1039`, `bird_dev_1045`, `bird_dev_1050`, `bird_dev_1060`, `bird_dev_1076`, `bird_dev_1086`, `bird_dev_1098`, and `bird_dev_1100`.

Warm-start losses occurred on `bird_dev_1038`, `bird_dev_1042`, `bird_dev_1061`, `bird_dev_1069`, `bird_dev_1073`, `bird_dev_1078`, `bird_dev_1079`, `bird_dev_1083`, `bird_dev_1092`, `bird_dev_1101`, `bird_dev_1108`, and `bird_dev_1145`.

## The only transferred-skill reuse

Spider question `spider_dev_571` reused `student_course_transcript_counts`:

```text
Question:
How many times at most can a course enrollment result show in different transcripts?
Also show the course enrollment id.

Skill outputs:
student_course_id, transcript_count

Skill lineage:
Student_Enrolment_Courses, Transcript_Contents

Operators:
join, project, aggregate
```

The final SQL executed the stored skill unchanged and answered correctly. Its contribution record shows that `student_course_id` and `transcript_count` were used in projection, filtering, and aggregation. However, regeneration ablation returned `inconclusive`, so this is a successful reuse association rather than a demonstrated causal win.

No BIRD seed skill was selected. No online Qwen skill was reused on either dataset.

## Why the warm-start condition was expensive

The dominant new expense was candidate verification:

| Dataset | Candidate-choice tokens | Candidate-choice calls | Candidates rejected |
|---|---:|---:|---:|
| Spider | 440,258 | 305 | 104 |
| BIRD | 1,076,089 | 642 | 232 |
| Total | **1,516,347** | **947** | **336** |

Candidate-choice calls account for most of the 1.71 million token increase. The conservative verifier prevented questionable reuse, but it paid a large cost to reject almost every candidate. This is safe but inefficient.

View-generation cost itself did not explain most of the overhead. Spider warm-start view-generation tokens were slightly lower than no graph, while BIRD warm-start view-generation tokens were moderately higher. Verification, final-skill extraction, generated tests, and learning accounted for the remaining difference.

## Why almost every reuse candidate was rejected

The retrieval funnel identifies the main failure precisely:

| Dataset | N×1 chunk requests | Requests with indexed candidates | Requests with a semantic shortlist | Verified reuse | Verifier chose `NONE` |
|---|---:|---:|---:|---:|---:|
| Spider | 156 | 156 | 105 | 1 | 104 |
| BIRD | 387 | 387 | 232 | 0 | 232 |
| Total | 543 | 543 | 337 | 1 | 336 |

The registry therefore did not fail to find skills. Every chunk request found structurally indexed candidates. Semantic ranking also produced a shortlist for 337 requests, with average positive top similarity near 0.68 on Spider and 0.67 on BIRD. The final Qwen selector rejected 336 of those 337 shortlists.

The underlying mismatch is between holistic N×1 requests and the strict verifier. N×1 requests carry the complete rewritten question and a chunk's tables, but intentionally leave `required_outputs` and `required_grain` empty. Their category is also ignored during holistic contract matching. As a result, deterministic Stage 2 and provenance compatibility cannot prove that a stored skill has the required output shape and grain. No rejection in this experiment was recorded by the qualified-output provenance check because there was no qualified requested output to test.

The final selector is then instructed to reuse only when outputs, grain, filters, aggregation, lineage, and operators are all guaranteed, and to choose `NONE` whenever anything is uncertain. Qwen follows that reject-biased instruction literally. Even high-similarity candidates such as `department_degree_counts`, with similarities around 0.77 to 0.81 for related Spider questions, were rejected because the request did not provide an explicit contract that could establish a guaranteed match.

Risky stored categories such as aggregation and join also request at least three verifier votes. This explains why 337 shortlisted requests produced 947 candidate-choice calls. The multiple-vote guard improves safety but multiplies the cost of an abstention.

Table-domain filtering was active and conservative. It rejected 1,872 Spider candidate occurrences and 774 BIRD candidate occurrences because their lineage read tables outside the current schema chunk. This avoided cross-chunk misuse, but it was not the primary bottleneck because every request still began with indexed candidates.

The practical failure chain was therefore:

```text
broad table-index candidates
        ↓
semantic shortlist succeeds
        ↓
holistic request has no outputs or grain
        ↓
deterministic compatibility cannot prove a match
        ↓
reject-biased Qwen verifier chooses NONE
        ↓
generate a fresh CTE after paying verification cost
```

This also explains why provenance storage alone did not help. Provenance can reject a wrong qualified lineage or operator structure only when the new request states what lineage or structure is required. The current N×1 request representation does not expose enough of that information.

## Why accuracy changed without reuse

The two conditions are not identical after a retrieval miss. The warm-start planner is told that a generated view was created because candidate reuse was rejected, while the no-graph planner is told that memory was off. Seed skill names can also change generated CTE naming through collision handling, and the read-write arm performs extraction, validation, and admission calls between questions. Local inference can vary even at temperature zero because GPU execution is not guaranteed to be bitwise deterministic.

Therefore, a warm-start win without an executed skill is not evidence that memory supplied the answer. It is a pipeline or generation flip. This is why the paired wins and losses are reported separately from actual reuse and causal ablation.

## CTE-generation reliability

| Dataset | Condition | Questions with no generated CTE | Correct among those questions |
|---|---|---:|---:|
| Spider | No graph | 28 | 6 |
| Spider | Warm start | 26 | 7 |
| BIRD | No graph | 51 | 15 |
| BIRD | Warm start | 57 | 15 |

The graph slightly reduced CTE-generation failure on Spider but increased it on BIRD. T=5 did not guarantee a usable CTE from Qwen. It only provided five opportunities to generate and validate one.

## Read-write graph evolution

| Dataset | Seed size | Final size | Added skills | Removed skills | Retired skills |
|---|---:|---:|---:|---:|---:|
| Spider | 28 | 30 | 2 | 0 | 0 |
| BIRD | 35 | 36 | 1 | 0 | 0 |

Spider added:

- `department_degree_counts_29`
- `students_with_distinct_addresses`

BIRD added:

- `leagues_by_country`

None of these online-added skills was reused later in the stream.

The evolved memory also exposes admission-quality issues. `department_degree_counts_29` is semantically close to the existing `department_degree_counts`, but it uses `num_degrees` instead of `degree_count`, so the current equivalence logic did not merge it. `students_with_distinct_addresses` was stored with a `CONFLICTS_WITH` relation to an existing similar skill. `leagues_by_country` exposes ambiguous output names as `name` and `name:1`, which is executable but not an ideal reusable contract. These cases suggest that read-write admission needs stronger semantic duplicate detection and output-name normalization before it should be trusted for long-running autonomous memory growth.

## Interpretation

### What worked

- The GPT seed graphs loaded into a different model without schema or contract failures.
- The original seed graphs remained unchanged.
- Qwen evolved separate registries with validated online skills.
- Conservative verification avoided incorrect executed reuse.
- One transferred Spider skill was selected, executed unchanged, and contributed to a correct answer.
- Spider warm-start accuracy improved by five answers.

### What did not work

- Only 1 of 207 questions reused a transferred skill.
- BIRD reused no transferred skills.
- No reuse was established as a causal win.
- The verifier rejected 336 proposed matches.
- Pooled tokens increased by 24.2%.
- Pooled calls increased by 49.2%.
- BIRD accuracy decreased by one answer.
- Newly learned skills were not reused.
- At least one apparent semantic duplicate entered the evolved registry.

### Scientific conclusion

The experiment does not support the claim that a GPT-generated provenance registry transfers efficiently to Qwen3 8B. It supports a narrower claim: the registry is technically portable across models, conservative verification prevents most unsafe reuse, and one skill was successfully consumed by Qwen. The current verifier is too expensive and too reluctant for practical cross-model reuse.

The pooled four-answer improvement should not be credited to reuse. Seventeen of the eighteen warm-start wins did not reuse a stored skill, all fourteen losses also occurred without reuse, and the one reuse win had inconclusive causal ablation. The warm-start pipeline changes prompts, verification calls, generation opportunities, and planner behavior even when no candidate is accepted.

## Limitations

This is a cross-model replay experiment, not an unseen generalization experiment. The GPT seed registries were built from the same ordered question streams later answered by Qwen. A clean generalization study should build memory from a training prefix or separate workload and evaluate only on unseen later questions.

Each condition was run once. Although local inference used temperature zero, generation can still vary through runtime behavior and the two conditions execute different prompt and call sequences. Paired flips without actual reuse should not be interpreted as memory effects.

The no-graph arm disables cross-question learning, while the warm-start arm permits online admission and evidence updates. This comparison measures the complete read-write warm-start system. It does not isolate read-only transfer from online evolution.

## Recommended next ablations

1. Compare no graph, frozen read-only registry, and evolving read-write registry under identical settings.
2. Evaluate on unseen questions rather than replaying the memory-construction stream.
3. Replace LLM verification for obvious contract-safe matches with deterministic acceptance and reserve voting for risky candidates.
4. Compare one verifier vote against three risky-category votes to quantify safety and cost.
5. Strengthen semantic duplicate detection and canonical output naming during admission.
6. Report retrieval precision and recall using manually labeled compatible skills, not only final SQL accuracy.

## Artifacts

- [Spider no-graph results](runs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_spider_B_Baseline_AVSQL.json)
- [Spider warm-start results](runs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_spider_S_ColdStart_Seed.json)
- [Spider summary](runs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_spider_summary.json)
- [Spider evolved graph](graphs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_spider_S_ColdStart_Seed/student_transcripts_tracking.json)
- [Spider episodes](graphs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_spider_S_ColdStart_Seed/student_transcripts_tracking.episodes.jsonl)
- [Spider evidence ledger](graphs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_spider_S_ColdStart_Seed/student_transcripts_tracking.ledger.jsonl)
- [BIRD no-graph results](runs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_bird_B_Baseline_AVSQL.json)
- [BIRD warm-start results](runs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_bird_S_ColdStart_Seed.json)
- [BIRD summary](runs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_bird_summary.json)
- [BIRD evolved graph](graphs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_bird_S_ColdStart_Seed/european_football_2.json)
- [BIRD episodes](graphs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_bird_S_ColdStart_Seed/european_football_2.episodes.jsonl)
- [BIRD evidence ledger](graphs/local_transfer_qwen3_8b_t5/qwen3_8b_transfer_t5_bird_S_ColdStart_Seed/european_football_2.ledger.jsonl)
