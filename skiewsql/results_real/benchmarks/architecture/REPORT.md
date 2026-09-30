# Current architecture benchmark: semantic adaptive routing

> Fresh run on 30 September 2026. This is the active report. The retired focused-holistic arm is deliberately excluded from the interface, run set, and comparison tables.

## Bottom line

Adaptive is **not universally more accurate** in this sample. It ties AV-SQL without a graph overall at **20/60 (33.3%)**, while using **22.2% fewer tokens** and generating **19 instead of 106 CTEs**. The tie hides a strong dataset interaction: adaptive gains four answers on Spider and loses four on BIRD. All four methods fail all 20 selected Spider2-lite questions.

The good news is that semantic routing works very well on the selected Spider stream: adaptive reaches **17/20 (85%)**, compared with 13/20 for AV-SQL without graph, while using 78.0% fewer tokens. The bad news is that moderate BIRD questions still enter aggressive AV graph reuse, producing 13 non-trivial negative-reuse failures.

## Experimental setup

- Spider: first 20 questions from `student_transcripts_tracking`.
- BIRD: first 20 questions from `european_football_2`.
- Spider2-lite: all 15 `bank_sales_trading` plus all 5 `education_business` questions.
- Model: local Ollama `gemma3:4b`, temperature 0.
- Common settings: 1,000-token schema chunks, maximum 3 subgoals, 1 view-validation attempt, 1 SQL repair, 1 self-consistency pass, no value linking, retrieval threshold 0.6.
- Each graph-enabled dataset run starts with an empty graph and grows it sequentially question by question. Graphs are not shared between architectures or datasets.
- `N` is the number of schema chunks and `M` is the number of dependency subgoals. Dependency mode aligns every one of the `M` subgoals against all `N` chunks.

## Accuracy by dataset

| Method | Spider | BIRD | Spider2-lite | Overall |
|---|---:|---:|---:|---:|
| AV-SQL, no graph | 13/20 (65.0%) | 7/20 (35.0%) | 0/20 (0.0%) | 20/60 (33.3%) |
| AV-SQL + graph | 12/20 (60.0%) | 2/20 (10.0%) | 0/20 (0.0%) | 14/60 (23.3%) |
| Dependency N×M + graph | 11/20 (55.0%) | 3/20 (15.0%) | 0/20 (0.0%) | 14/60 (23.3%) |
| Adaptive + graph | 17/20 (85.0%) | 3/20 (15.0%) | 0/20 (0.0%) | 20/60 (33.3%) |

## Pooled cost, graph, and reuse results

`Measured time` is the sum of per-question pipeline timers in the result rows. It excludes dataset preparation and model loading. The Spider2-lite AV-graph run also had one 240-second question timeout, which is recorded separately and is not represented faithfully by that row timer.

| Method | Correct | Tokens | LLM/embed calls | CTEs generated | Questions with reuse | Negative reuse | Saved graph views | Measured time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AV-SQL, no graph | 20/60 | 904,664 | 375 | 106 | 0/60 | 0 (0 raw) | n/a | 410.58s |
| AV-SQL + graph | 14/60 | 659,198 | 290 | 10 | 54/60 | 33 (41 raw) | 11 | 294.66s |
| Dependency N×M + graph | 14/60 | 1,185,452 | 736 | 48 | 3/60 | 1 (3 raw) | 48 | 547.76s |
| Adaptive + graph | 20/60 | 704,243 | 466 | 19 | 19/60 | 15 (15 raw) | 19 | 393.94s |

Relative to AV-SQL without graph:

- AV-SQL + graph saves 27.1% of tokens and 90.6% of CTE generation, but loses 6 correct answers and incurs 33 non-trivial negative reuses.
- Dependency N×M also scores 14/60, uses 31.0% more tokens, and nearly doubles calls. Alignment alone accounts for 532,996 tokens and 384 calls.
- Adaptive preserves the same 20/60 accuracy, saves 22.2% of tokens and 82.1% of CTE generation, but makes 24.3% more calls because classification and alignment add many short calls.

## Detailed dataset metrics

| Dataset | Method | Correct | Tokens | Calls | Generated | Reuse-hit questions | Non-trivial negative reuse | Mean seconds/question |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Spider | AV-SQL, no graph | 13/20 | 168,122 | 108 | 35 | 0 | 0 | 3.51 |
| Spider | AV-SQL + graph | 12/20 | 121,253 | 92 | 3 | 18 | 0 | 2.95 |
| Spider | Dependency N×M + graph | 11/20 | 139,229 | 147 | 14 | 2 | 1 | 3.85 |
| Spider | Adaptive + graph | 17/20 | 37,024 | 68 | 1 | 1 | 0 | 1.86 |
| BIRD | AV-SQL, no graph | 7/20 | 410,544 | 133 | 44 | 0 | 0 | 7.13 |
| BIRD | AV-SQL + graph | 2/20 | 297,126 | 97 | 2 | 19 | 17 | 4.54 |
| BIRD | Dependency N×M + graph | 3/20 | 621,275 | 274 | 12 | 1 | 0 | 9.54 |
| BIRD | Adaptive + graph | 3/20 | 246,038 | 104 | 2 | 16 | 13 | 4.67 |
| Spider2-lite | AV-SQL, no graph | 0/20 | 325,998 | 134 | 27 | 0 | 0 | 9.88 |
| Spider2-lite | AV-SQL + graph | 0/20 | 240,819 | 101 | 5 | 17 | 16 | 7.24 |
| Spider2-lite | Dependency N×M + graph | 0/20 | 424,948 | 315 | 22 | 0 | 0 | 14.00 |
| Spider2-lite | Adaptive + graph | 0/20 | 421,181 | 294 | 16 | 2 | 2 | 13.17 |

## What adaptive actually selected

| Dataset | Route | Questions | Correct | Generated CTEs | Reuse-hit questions | Negative reuse | Tokens |
|---|---|---:|---:|---:|---:|---:|---:|
| Spider | Moderate → AV N×1 + graph | 2 | 2 (100.0%) | 1 | 1 | 0 | 17,746 |
| Spider | Easy → direct SQL | 18 | 15 (83.3%) | 0 | 0 | 0 | 19,278 |
| BIRD | Moderate → AV N×1 + graph | 17 | 3 (17.6%) | 2 | 16 | 13 | 240,543 |
| BIRD | Easy → direct SQL | 3 | 0 (0.0%) | 0 | 0 | 0 | 5,495 |
| Spider2-lite | Moderate → AV N×1 + graph | 4 | 0 (0.0%) | 3 | 2 | 2 | 62,673 |
| Spider2-lite | Hard → dependency N×M + graph | 16 | 0 (0.0%) | 13 | 0 | 0 | 358,508 |

Interpretation:

- Spider benefited because 18/20 questions bypassed views and graph retrieval. Direct SQL was correct on 15/18, and both moderate questions were correct.
- BIRD routed 17/20 questions to moderate AV+graph. Reusing two early views broadly over the stream saved cost but caused 13 negative-reuse failures. No question was classified hard.
- Spider2-lite routed 16/20 questions to hard N×M and 4/20 to moderate AV. This routing looks structurally plausible, but the local 4B model produced no correct final answers.

## Paired adaptive wins and losses

A win means adaptive is correct and the compared method is wrong on the same question. A loss is the reverse. A tie includes both-correct and both-wrong cases.

| Compared with | Spider W/L/T | BIRD W/L/T | Spider2-lite W/L/T | Overall W/L/T |
|---|---:|---:|---:|---:|
| AV-SQL, no graph | 5/1/14 | 0/4/16 | 0/0/20 | 5/5/50 |
| AV-SQL + graph | 7/2/11 | 2/1/17 | 0/0/20 | 9/3/48 |
| Dependency N×M + graph | 7/1/12 | 2/2/16 | 0/0/20 | 9/3/48 |

The most important paired comparison is adaptive versus AV-SQL without graph:

- Adaptive Spider wins: `spider_dev_509`, `spider_dev_510`, `spider_dev_513`, `spider_dev_519`, `spider_dev_520`.
- Adaptive Spider loss: `spider_dev_517`.
- Adaptive BIRD losses: `bird_dev_1020`, `bird_dev_1036`, `bird_dev_1038`, `bird_dev_1039`.
- Spider2-lite has 20 both-wrong ties. Overall this is 5 wins, 5 losses, and 50 ties.

## Token/call breakdown by stage

| Method | Stage | Tokens | Calls |
|---|---|---:|---:|
| AV-SQL, no graph | `av_view` | 283,830 | 160 |
| AV-SQL, no graph | `compose` | 227,106 | 56 |
| AV-SQL, no graph | `plan` | 208,210 | 56 |
| AV-SQL, no graph | `revise` | 146,292 | 38 |
| AV-SQL, no graph | `rewrite` | 21,871 | 60 |
| AV-SQL, no graph | `direct` | 17,355 | 5 |
| AV-SQL + graph | `compose` | 244,933 | 59 |
| AV-SQL + graph | `plan` | 224,090 | 59 |
| AV-SQL + graph | `revise` | 137,158 | 35 |
| AV-SQL + graph | `av_view` | 22,650 | 14 |
| AV-SQL + graph | `rewrite` | 21,847 | 60 |
| AV-SQL + graph | `embed` | 5,030 | 62 |
| AV-SQL + graph | `direct` | 3,490 | 1 |
| Dependency N×M + graph | `align` | 532,996 | 384 |
| Dependency N×M + graph | `generate` | 240,168 | 109 |
| Dependency N×M + graph | `decompose` | 103,274 | 60 |
| Dependency N×M + graph | `compose` | 84,670 | 38 |
| Dependency N×M + graph | `direct` | 78,639 | 22 |
| Dependency N×M + graph | `plan` | 72,430 | 38 |
| Dependency N×M + graph | `revise` | 51,391 | 20 |
| Dependency N×M + graph | `rewrite` | 21,844 | 60 |
| Dependency N×M + graph | `embed` | 40 | 5 |
| Adaptive + graph | `align` | 175,728 | 144 |
| Adaptive + graph | `compose` | 133,609 | 31 |
| Adaptive + graph | `plan` | 121,822 | 31 |
| Adaptive + graph | `revise` | 66,338 | 21 |
| Adaptive + graph | `generate` | 57,039 | 39 |
| Adaptive + graph | `direct` | 40,068 | 30 |
| Adaptive + graph | `difficulty` | 36,019 | 60 |
| Adaptive + graph | `decompose` | 31,026 | 16 |
| Adaptive + graph | `rewrite` | 21,858 | 60 |
| Adaptive + graph | `av_view` | 19,068 | 11 |
| Adaptive + graph | `embed` | 1,668 | 23 |

## Conclusions

1. **Keep adaptive as the research direction, but do not claim a universal accuracy win.** This run supports an efficiency claim at equal pooled accuracy and a strong Spider result.
2. **Do not enable aggressive graph reuse by default for moderate questions yet.** BIRD's high reuse rate is mostly harmful. Compatibility needs stronger grain/filter/output checks or a verifier before a saved view can replace fresh AV generation.
3. **Easy-question bypass is the clearest success.** It removes unnecessary views, graph lookups, and planner calls while improving Spider accuracy.
4. **Dependency N×M needs cheaper alignment.** It is safer than broad AV reuse here, but its 384 alignment calls and 532,996 alignment tokens do not produce an accuracy gain.
5. **Spider2-lite remains unresolved.** Because all methods score zero, this subset cannot distinguish architectures with the current local model. A stronger model and error-focused prompt/schema debugging are required before drawing architectural conclusions from it.

## Reproduction and artifacts

Run all four arms with:

```bash
bash skiewsql/results_real/benchmarks/architecture/run_current_benchmark.sh
python skiewsql/results_real/benchmarks/architecture/analyze_current_benchmark.py
```

Raw per-question outputs and the machine-readable aggregate are under `runs/current/`. Grown graphs are under `graphs/current/`. Per-process logs are under `logs/current/`.

## Validity limits

This is a controlled architecture test, not a publication-grade benchmark: each named dataset sample covers only one or two databases, uses a small local model, and contains 20 questions. Results may also vary across local inference runs despite temperature 0. The next confirmation should cover more database domains and use a stronger fixed model.
