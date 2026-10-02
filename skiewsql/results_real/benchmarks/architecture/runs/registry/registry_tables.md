## Accuracy

| Method | Run | Spider | BIRD | Spider2-lite | Overall |
|---|---|---:|---:|---:|---:|
| AV-SQL, no graph | before | 13/20 | 7/20 | 0/20 | 20/60 |
| AV-SQL, no graph | registry | 15/20 | 5/20 | 0/20 | 20/60 |
| Adaptive + graph | before | 17/20 | 3/20 | 0/20 | 20/60 |
| Adaptive + graph | registry | 17/20 | 4/20 | 0/20 | 21/60 |

## Cost and reuse per dataset

| Dataset | Method | Run | Correct | Tokens (learning) | Calls (learning) | CTEs generated | Reuse questions | Neg. reuse (old def / referenced) | Executed reuses | Causal +/− | Align calls | Prefetch hits | Admitted | Verifier rejects | Graph |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Spider | AV-SQL, no graph | before | 13/20 | 168,122 (0) | 108 (0) | 35 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 2 |
| Spider | AV-SQL, no graph | registry | 15/20 | 165,839 (0) | 108 (0) | 34 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 2 |
| Spider | Adaptive + graph | before | 17/20 | 37,024 (0) | 68 (0) | 1 | 1 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 1 |
| Spider | Adaptive + graph | registry | 17/20 | 49,281 (8,982) | 88 (20) | 2 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 0 |
| BIRD | AV-SQL, no graph | before | 7/20 | 410,544 (0) | 133 (0) | 44 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 3 |
| BIRD | AV-SQL, no graph | registry | 5/20 | 415,346 (0) | 135 (0) | 38 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 3 |
| BIRD | Adaptive + graph | before | 3/20 | 246,038 (0) | 104 (0) | 2 | 16 | 13 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 2 |
| BIRD | Adaptive + graph | registry | 4/20 | 351,967 (9,337) | 150 (15) | 31 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 0 |
| Spider2-lite | AV-SQL, no graph | before | 0/20 | 325,998 (0) | 134 (0) | 27 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 3 |
| Spider2-lite | AV-SQL, no graph | registry | 0/20 | 339,027 (0) | 136 (0) | 29 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 | 0 | 0 | 2 |
| Spider2-lite | Adaptive + graph | before | 0/20 | 421,181 (0) | 294 (0) | 16 | 2 | 2 / 0 | 0 | 0/0 | 144 | 0 | 0 | 0 | 16 |
| Spider2-lite | Adaptive + graph | registry | 0/20 | 440,777 (12,450) | 323 (16) | 30 | 0 | 0 / 0 | 0 | 0/0 | 138 | 0 | 6 | 0 | 6 |

## Routes (adaptive)

- before Spider: av_nx1_graph 2, direct_sql 18
- before BIRD: av_nx1_graph 17, direct_sql 3
- before Spider2-lite: av_nx1_graph 4, dependency_nxm_graph 16
- registry Spider: av_nx1_graph 2, direct_sql 18
- registry BIRD: av_nx1_graph 16, direct_sql 4
- registry Spider2-lite: av_nx1_graph 4, dependency_nxm_graph 16

## Paired comparisons (W/L/T, wins listed)

- **registry adaptive vs before adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 1/0/19 (wins ['bird_dev_1038'], losses —); Spider2-lite 0/0/20 (wins —, losses —)
- **registry adaptive vs registry no-graph**: Spider 4/2/14 (wins ['spider_dev_509', 'spider_dev_519', 'spider_dev_520', 'spider_dev_521'], losses ['spider_dev_507', 'spider_dev_517']); BIRD 2/3/15 (wins ['bird_dev_1033', 'bird_dev_1038'], losses ['bird_dev_1020', 'bird_dev_1035', 'bird_dev_1039']); Spider2-lite 0/0/20 (wins —, losses —)
- **registry no-graph vs before no-graph**: Spider 3/1/16 (wins ['spider_dev_507', 'spider_dev_510', 'spider_dev_513'], losses ['spider_dev_521']); BIRD 1/3/16 (wins ['bird_dev_1035'], losses ['bird_dev_1033', 'bird_dev_1036', 'bird_dev_1038']); Spider2-lite 0/0/20 (wins —, losses —)

## Registry-arm stage breakdown (tokens / calls, all datasets)

| Stage | Tokens | Calls |
|---|---:|---:|
| `align` | 168,296 | 138 |
| `compose` | 132,584 | 34 |
| `av_view` | 127,413 | 64 |
| `plan` | 119,559 | 34 |
| `revise` | 88,028 | 27 |
| `generate` | 63,163 | 44 |
| `difficulty` | 35,603 | 60 |
| `decompose` | 30,466 | 16 |
| `extract_final` | 26,810 | 45 |
| `direct` | 24,172 | 26 |
| `rewrite` | 21,702 | 60 |
| `gen_tests` | 3,959 | 6 |
| `embed` | 270 | 7 |
