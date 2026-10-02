# Adaptive architecture — implementation smoke results

**Status:** integration smoke test, **not** a controlled benchmark comparison.

> This is a historical smoke test of the retired schema-size router. The current adaptive router is direct SQL for easy questions, AV-SQL N×1 plus graph reuse for moderate questions, and dependency N×M plus graph reuse for hard questions.

The adaptive implementation was exercised with the Together backend on one question per selected dataset/database, config A only, with one view-generation attempt, one SQL-repair attempt, and value linking disabled. These runs validate loading, automatic routing, view generation/validation, final composition, execution scoring, token accounting, and serialization. They do not estimate aggregate accuracy and do not isolate the effect of memory or architecture.

| dataset | database / question | selected route | correct | generated | reused | tokens | seconds | outcome |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Spider | `world_1` / `spider_dev_702` | holistic | 1 | 1 | 0 | 9,214 | 105.60 | completed |
| BIRD | `card_games` / `bird_dev_340` | holistic | 0 | 1 | 0 | 15,608 | 176.61 | executing result mismatch |
| Spider2-lite | `log` / `local329` | holistic | 1 | 1 | 0 | 17,949 | 300.39 | completed |
| Spider2-lite | `bank_sales_trading` / `local074` | failed after entering holistic path | 0 | 0 reported | 0 | 21,816 | 600 cap | generated a graph view, timed out downstream |

Completed questions only: **2/3 correct**. All attempts: **2/4 correct with one timeout**. These fractions are descriptive only—the sample is too small and deliberately non-random.

Raw temporary outputs:

- `/tmp/skiew_adaptive_spider_together/adaptive_smoke_spider_A_SkiewSQL.json`
- `/tmp/skiew_adaptive_bird_together/adaptive_smoke_bird_A_SkiewSQL.json`
- `/tmp/skiew_adaptive_spider2_log_together/adaptive_smoke_spider2lite_A_SkiewSQL.json`
- `/tmp/skiew_adaptive_spider2_together/adaptive_smoke_spider2lite_A_SkiewSQL.json`

## Routing audit over real local schemas

At the configured 8k-token chunk budget:

| dataset | databases audited | one chunk | multi-chunk |
|---|---:|---:|---:|
| Spider dev | 20 | 20 | 0 |
| BIRD dev | 11 | 11 | 0 |
| BIRD Mini-Dev | 11 | 11 | 0 |
| Spider2-lite local | 30 | 30 | 0 |

Consequently, adaptive mode deliberately chooses the holistic route for every local database. The new focused-holistic and dependency-N×M decisions matter on BEAVER/cloud-scale schemas, not these local schemas.

## Relevant older full-run comparisons (not the new adaptive code)

| benchmark | holistic / v2m | N×M | other baseline |
|---|---:|---:|---:|
| Spider2-lite common 121 | **40/121 = 33.1%** | 17/121 = 14.0% | external AV-SQL: ~46/121 = 38.0% |
| BEAVER 108, matched `BV108` files | 12/108 = 11.1% | **13/108 = 12.0%** | AV-SQL-style: 10/108 = 9.3% |

Those results motivated the router, but they are not measurements of `--architecture auto`.

## Blockers to a controlled full comparison

- OpenAI returned quota-exhausted (HTTP 429).
- Together took 105–300 seconds per completed local question. A full multi-configuration sweep would take many hours/days at the configured free-tier rate.
- The BEAVER MariaDB endpoint at `127.0.0.1:3307` was unavailable (`connection refused`), so the decisive real multi-chunk benchmark could not be launched.

A defensible result still requires identical-question runs of `auto`, `nx1`, and `nxm` (plus the no-memory baseline), preferably on BEAVER after MariaDB is restored. Until then, only implementation and integration correctness—not an accuracy/cost improvement—has been established.
