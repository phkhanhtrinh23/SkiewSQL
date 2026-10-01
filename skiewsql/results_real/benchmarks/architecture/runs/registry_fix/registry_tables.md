## Accuracy

| Method | Run | Spider | BIRD | Spider2-lite | Overall |
|---|---|---:|---:|---:|---:|
| AV-SQL, no graph | before | 13/20 | 7/20 | 0/20 | 20/60 |
| AV-SQL, no graph | registry | 15/20 | 5/20 | 0/20 | 20/60 |
| AV-SQL, no graph | fixed | 17/20 | 3/20 | 1/20 | 21/60 |
| Adaptive + graph | before | 17/20 | 3/20 | 0/20 | 20/60 |
| Adaptive + graph | registry | 17/20 | 4/20 | 0/20 | 21/60 |
| Adaptive + graph | fixed | 17/20 | 3/20 | 0/20 | 20/60 |

## Cost and reuse per dataset

| Dataset | Method | Run | Correct | Tokens (learning) | Calls (learning) | CTEs generated | Reuse questions | Neg. reuse (old def / referenced) | Executed reuses | Causal +/− | Align calls | Prefetch hits (ungrounded) | Admitted | Verifier rejects | Graph |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Spider | AV-SQL, no graph | before | 13/20 | 168,122 (0) | 108 (0) | 35 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider | AV-SQL, no graph | registry | 15/20 | 165,839 (0) | 108 (0) | 34 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider | AV-SQL, no graph | fixed | 17/20 | 169,830 (0) | 109 (0) | 31 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider | Adaptive + graph | before | 17/20 | 37,024 (0) | 68 (0) | 1 | 1 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 1 |
| Spider | Adaptive + graph | registry | 17/20 | 49,281 (8,982) | 88 (20) | 2 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| Spider | Adaptive + graph | fixed | 17/20 | 47,952 (11,674) | 89 (23) | 2 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 1 | 0 | 1 |
| BIRD | AV-SQL, no graph | before | 7/20 | 410,544 (0) | 133 (0) | 44 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 3 |
| BIRD | AV-SQL, no graph | registry | 5/20 | 415,346 (0) | 135 (0) | 38 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 3 |
| BIRD | AV-SQL, no graph | fixed | 3/20 | 413,281 (0) | 134 (0) | 41 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| BIRD | Adaptive + graph | before | 3/20 | 246,038 (0) | 104 (0) | 2 | 16 | 13 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| BIRD | Adaptive + graph | registry | 4/20 | 351,967 (9,337) | 150 (15) | 31 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| BIRD | Adaptive + graph | fixed | 3/20 | 365,792 (13,439) | 158 (20) | 37 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| Spider2-lite | AV-SQL, no graph | before | 0/20 | 325,998 (0) | 134 (0) | 27 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 3 |
| Spider2-lite | AV-SQL, no graph | registry | 0/20 | 339,027 (0) | 136 (0) | 29 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider2-lite | AV-SQL, no graph | fixed | 1/20 | 315,283 (0) | 131 (0) | 27 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider2-lite | Adaptive + graph | before | 0/20 | 421,181 (0) | 294 (0) | 16 | 2 | 2 / 0 | 0 | 0/0 | 144 | 0 (0) | 0 | 0 | 16 |
| Spider2-lite | Adaptive + graph | registry | 0/20 | 440,777 (12,450) | 323 (16) | 30 | 0 | 0 / 0 | 0 | 0/0 | 138 | 0 (0) | 6 | 0 | 6 |
| Spider2-lite | Adaptive + graph | fixed | 0/20 | 446,346 (9,362) | 323 (12) | 26 | 0 | 0 / 0 | 0 | 0/0 | 144 | 0 (0) | 2 | 0 | 2 |

## Routes (adaptive)

- before Spider: av_nx1_graph 2, direct_sql 18
- before BIRD: av_nx1_graph 17, direct_sql 3
- before Spider2-lite: av_nx1_graph 4, dependency_nxm_graph 16
- registry Spider: av_nx1_graph 2, direct_sql 18
- registry BIRD: av_nx1_graph 16, direct_sql 4
- registry Spider2-lite: av_nx1_graph 4, dependency_nxm_graph 16
- fixed Spider: av_nx1_graph 2, direct_sql 18
- fixed BIRD: av_nx1_graph 16, direct_sql 4
- fixed Spider2-lite: av_nx1_graph 4, dependency_nxm_graph 16

## Paired comparisons (W/L/T, wins listed)

- **fixed adaptive vs registry adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 2/3/15 (wins ['bird_dev_1034', 'bird_dev_1039'], losses ['bird_dev_1025', 'bird_dev_1032', 'bird_dev_1033']); Spider2-lite 0/0/20 (wins —, losses —)
- **fixed adaptive vs before adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 3/3/14 (wins ['bird_dev_1034', 'bird_dev_1038', 'bird_dev_1039'], losses ['bird_dev_1025', 'bird_dev_1032', 'bird_dev_1033']); Spider2-lite 0/0/20 (wins —, losses —)
- **fixed adaptive vs fixed no-graph**: Spider 1/1/18 (wins ['spider_dev_521'], losses ['spider_dev_517']); BIRD 1/1/18 (wins ['bird_dev_1034'], losses ['bird_dev_1021']); Spider2-lite 0/1/19 (wins —, losses ['local058'])
- **fixed no-graph vs registry no-graph**: Spider 3/1/16 (wins ['spider_dev_509', 'spider_dev_519', 'spider_dev_520'], losses ['spider_dev_507']); BIRD 2/4/14 (wins ['bird_dev_1021', 'bird_dev_1038'], losses ['bird_dev_1020', 'bird_dev_1025', 'bird_dev_1032', 'bird_dev_1035']); Spider2-lite 1/0/19 (wins ['local058'], losses —)
- **registry adaptive vs before adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 1/0/19 (wins ['bird_dev_1038'], losses —); Spider2-lite 0/0/20 (wins —, losses —)
- **registry adaptive vs registry no-graph**: Spider 4/2/14 (wins ['spider_dev_509', 'spider_dev_519', 'spider_dev_520', 'spider_dev_521'], losses ['spider_dev_507', 'spider_dev_517']); BIRD 2/3/15 (wins ['bird_dev_1033', 'bird_dev_1038'], losses ['bird_dev_1020', 'bird_dev_1035', 'bird_dev_1039']); Spider2-lite 0/0/20 (wins —, losses —)
- **registry no-graph vs before no-graph**: Spider 3/1/16 (wins ['spider_dev_507', 'spider_dev_510', 'spider_dev_513'], losses ['spider_dev_521']); BIRD 1/3/16 (wins ['bird_dev_1035'], losses ['bird_dev_1033', 'bird_dev_1036', 'bird_dev_1038']); Spider2-lite 0/0/20 (wins —, losses —)

## Stage breakdown, adaptive `fixed` run (tokens / calls, all datasets)

| Stage | Tokens | Calls |
|---|---:|---:|
| `align` | 175,804 | 144 |
| `compose` | 132,031 | 33 |
| `av_view` | 126,291 | 64 |
| `plan` | 120,072 | 33 |
| `revise` | 93,311 | 30 |
| `generate` | 62,282 | 45 |
| `difficulty` | 35,620 | 60 |
| `decompose` | 30,947 | 16 |
| `extract_final` | 28,052 | 48 |
| `direct` | 27,320 | 27 |
| `rewrite` | 21,715 | 60 |
| `gen_tests` | 5,500 | 6 |
| `promote_describe` | 923 | 1 |
| `embed` | 222 | 3 |
