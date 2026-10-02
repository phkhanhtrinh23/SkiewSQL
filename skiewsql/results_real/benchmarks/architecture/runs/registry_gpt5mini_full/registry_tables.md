## Accuracy

| Method | Run | Spider | BIRD | Spider2-lite | Overall |
|---|---|---:|---:|---:|---:|
| AV-SQL, no graph | before | 13/20 | 7/20 | 0/20 | 20/60 |
| AV-SQL, no graph | registry | 15/20 | 5/20 | 0/20 | 20/60 |
| AV-SQL, no graph | fixed | 17/20 | 3/20 | 1/20 | 21/60 |
| AV-SQL, no graph | gpt5mini | 17/20 | 6/20 | 2/20 | 25/60 |
| AV-SQL, no graph | gpt5full | 47/78 | 51/129 | 3/20 | 101/227 |
| Adaptive + graph | before | 17/20 | 3/20 | 0/20 | 20/60 |
| Adaptive + graph | registry | 17/20 | 4/20 | 0/20 | 21/60 |
| Adaptive + graph | fixed | 17/20 | 3/20 | 0/20 | 20/60 |
| Adaptive + graph | gpt5mini | 17/20 | 4/20 | 0/20 | 21/60 |
| Adaptive + graph | gpt5full | 41/78 | 49/129 | 1/20 | 91/227 |

## Cost and reuse per dataset

| Dataset | Method | Run | Correct | Tokens (learning) | Calls (learning) | CTEs generated | Reuse questions | Neg. reuse (old def / referenced) | Executed reuses | Causal +/− | Align calls | Prefetch hits (ungrounded) | Admitted | Verifier rejects | Graph |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Spider | AV-SQL, no graph | before | 13/20 | 168,122 (0) | 108 (0) | 35 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider | AV-SQL, no graph | registry | 15/20 | 165,839 (0) | 108 (0) | 34 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider | AV-SQL, no graph | fixed | 17/20 | 169,830 (0) | 109 (0) | 31 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider | AV-SQL, no graph | gpt5mini | 17/20 | 123,061 (0) | 97 (0) | 23 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 1 |
| Spider | AV-SQL, no graph | gpt5full | 47/78 | 420,286 (0) | 346 (0) | 33 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| Spider | Adaptive + graph | before | 17/20 | 37,024 (0) | 68 (0) | 1 | 1 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 1 |
| Spider | Adaptive + graph | registry | 17/20 | 49,281 (8,982) | 88 (20) | 2 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| Spider | Adaptive + graph | fixed | 17/20 | 47,952 (11,674) | 89 (23) | 2 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 1 | 0 | 1 |
| Spider | Adaptive + graph | gpt5mini | 17/20 | 44,354 (13,441) | 95 (24) | 0 | 1 | 0 / 0 | 1 | 0/0 | 0 | 0 (0) | 2 | 0 | 2 |
| Spider | Adaptive + graph | gpt5full | 41/78 | 292,689 (76,491) | 483 (115) | 18 | 2 | 0 / 1 | 2 | 0/0 | 17 | 1 (0) | 33 | 1 | 33 |
| BIRD | AV-SQL, no graph | before | 7/20 | 410,544 (0) | 133 (0) | 44 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 3 |
| BIRD | AV-SQL, no graph | registry | 5/20 | 415,346 (0) | 135 (0) | 38 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 3 |
| BIRD | AV-SQL, no graph | fixed | 3/20 | 413,281 (0) | 134 (0) | 41 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| BIRD | AV-SQL, no graph | gpt5mini | 6/20 | 259,467 (0) | 113 (0) | 15 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 1 |
| BIRD | AV-SQL, no graph | gpt5full | 51/129 | 1,672,555 (0) | 732 (0) | 123 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| BIRD | Adaptive + graph | before | 3/20 | 246,038 (0) | 104 (0) | 2 | 16 | 13 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| BIRD | Adaptive + graph | registry | 4/20 | 351,967 (9,337) | 150 (15) | 31 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| BIRD | Adaptive + graph | fixed | 3/20 | 365,792 (13,439) | 158 (20) | 37 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 0 |
| BIRD | Adaptive + graph | gpt5mini | 4/20 | 172,492 (44,022) | 154 (38) | 12 | 0 | 0 / 0 | 0 | 0/0 | 36 | 0 (0) | 18 | 0 | 18 |
| BIRD | Adaptive + graph | gpt5full | 49/129 | 794,543 (122,553) | 881 (151) | 48 | 0 | 0 / 0 | 0 | 0/0 | 126 | 0 (0) | 24 | 0 | 24 |
| Spider2-lite | AV-SQL, no graph | before | 0/20 | 325,998 (0) | 134 (0) | 27 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 3 |
| Spider2-lite | AV-SQL, no graph | registry | 0/20 | 339,027 (0) | 136 (0) | 29 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider2-lite | AV-SQL, no graph | fixed | 1/20 | 315,283 (0) | 131 (0) | 27 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 2 |
| Spider2-lite | AV-SQL, no graph | gpt5mini | 2/20 | 290,015 (0) | 129 (0) | 33 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 4 |
| Spider2-lite | AV-SQL, no graph | gpt5full | 3/20 | 291,690 (0) | 131 (0) | 38 | 0 | 0 / 0 | 0 | 0/0 | 0 | 0 (0) | 0 | 0 | 4 |
| Spider2-lite | Adaptive + graph | before | 0/20 | 421,181 (0) | 294 (0) | 16 | 2 | 2 / 0 | 0 | 0/0 | 144 | 0 (0) | 0 | 0 | 16 |
| Spider2-lite | Adaptive + graph | registry | 0/20 | 440,777 (12,450) | 323 (16) | 30 | 0 | 0 / 0 | 0 | 0/0 | 138 | 0 (0) | 6 | 0 | 6 |
| Spider2-lite | Adaptive + graph | fixed | 0/20 | 446,346 (9,362) | 323 (12) | 26 | 0 | 0 / 0 | 0 | 0/0 | 144 | 0 (0) | 2 | 0 | 2 |
| Spider2-lite | Adaptive + graph | gpt5mini | 0/20 | 407,791 (49,237) | 336 (36) | 41 | 0 | 0 / 0 | 0 | 0/0 | 144 | 0 (0) | 16 | 0 | 16 |
| Spider2-lite | Adaptive + graph | gpt5full | 1/20 | 436,110 (56,350) | 512 (44) | 37 | 0 | 0 / 0 | 0 | 0/0 | 171 | 0 (0) | 21 | 0 | 21 |

## Reuse over the stream (adaptive: executed reuses, first half / second half of each DB)

- before: Spider 0/0, BIRD 0/0, Spider2-lite 0/0
- registry: Spider 0/0, BIRD 0/0, Spider2-lite 0/0
- fixed: Spider 0/0, BIRD 0/0, Spider2-lite 0/0
- gpt5mini: Spider 0/1, BIRD 0/0, Spider2-lite 0/0
- gpt5full: Spider 0/2, BIRD 0/0, Spider2-lite 0/0

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
- gpt5mini Spider: av_nx1_graph 2, direct_sql 18
- gpt5mini BIRD: dependency_nxm_graph 4, direct_sql 16
- gpt5mini Spider2-lite: av_nx1_graph 2, dependency_nxm_graph 16, direct_sql 2
- gpt5full Spider: av_nx1_graph 15, dependency_nxm_graph 3, direct_sql 60
- gpt5full BIRD: av_nx1_graph 7, dependency_nxm_graph 14, direct_sql 108
- gpt5full Spider2-lite: dependency_nxm_graph 19, direct_sql 1

## Paired comparisons (W/L/T, wins listed)

- **gpt5full adaptive vs gpt5full no-graph**: Spider 1/7/70 (wins ['spider_dev_581'], losses ['spider_dev_529', 'spider_dev_530', 'spider_dev_535', 'spider_dev_539', 'spider_dev_557', 'spider_dev_575', 'spider_dev_576']); BIRD 12/14/103 (wins ['bird_dev_1036', 'bird_dev_1047', 'bird_dev_1048', 'bird_dev_1052', 'bird_dev_1057', 'bird_dev_1065', 'bird_dev_1082', 'bird_dev_1095', 'bird_dev_1105', 'bird_dev_1109', 'bird_dev_1129', 'bird_dev_1134'], losses ['bird_dev_1067', 'bird_dev_1070', 'bird_dev_1071', 'bird_dev_1087', 'bird_dev_1088', 'bird_dev_1090', 'bird_dev_1099', 'bird_dev_1101', 'bird_dev_1110', 'bird_dev_1112', 'bird_dev_1124', 'bird_dev_1130', 'bird_dev_1136', 'bird_dev_1147']); Spider2-lite 0/2/18 (wins —, losses ['local058', 'local059'])
- **gpt5mini adaptive vs gpt5mini no-graph**: Spider 0/0/20 (wins —, losses —); BIRD 1/3/16 (wins ['bird_dev_1022'], losses ['bird_dev_1020', 'bird_dev_1037', 'bird_dev_1038']); Spider2-lite 0/2/18 (wins —, losses ['local300', 'local301'])
- **gpt5mini adaptive vs fixed (gemma) adaptive**: Spider 2/2/16 (wins ['spider_dev_507', 'spider_dev_517'], losses ['spider_dev_512', 'spider_dev_525']); BIRD 3/2/15 (wins ['bird_dev_1022', 'bird_dev_1032', 'bird_dev_1033'], losses ['bird_dev_1034', 'bird_dev_1038']); Spider2-lite 0/0/20 (wins —, losses —)
- **fixed adaptive vs registry adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 2/3/15 (wins ['bird_dev_1034', 'bird_dev_1039'], losses ['bird_dev_1025', 'bird_dev_1032', 'bird_dev_1033']); Spider2-lite 0/0/20 (wins —, losses —)
- **fixed adaptive vs before adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 3/3/14 (wins ['bird_dev_1034', 'bird_dev_1038', 'bird_dev_1039'], losses ['bird_dev_1025', 'bird_dev_1032', 'bird_dev_1033']); Spider2-lite 0/0/20 (wins —, losses —)
- **fixed adaptive vs fixed no-graph**: Spider 1/1/18 (wins ['spider_dev_521'], losses ['spider_dev_517']); BIRD 1/1/18 (wins ['bird_dev_1034'], losses ['bird_dev_1021']); Spider2-lite 0/1/19 (wins —, losses ['local058'])
- **fixed no-graph vs registry no-graph**: Spider 3/1/16 (wins ['spider_dev_509', 'spider_dev_519', 'spider_dev_520'], losses ['spider_dev_507']); BIRD 2/4/14 (wins ['bird_dev_1021', 'bird_dev_1038'], losses ['bird_dev_1020', 'bird_dev_1025', 'bird_dev_1032', 'bird_dev_1035']); Spider2-lite 1/0/19 (wins ['local058'], losses —)
- **registry adaptive vs before adaptive**: Spider 0/0/20 (wins —, losses —); BIRD 1/0/19 (wins ['bird_dev_1038'], losses —); Spider2-lite 0/0/20 (wins —, losses —)
- **registry adaptive vs registry no-graph**: Spider 4/2/14 (wins ['spider_dev_509', 'spider_dev_519', 'spider_dev_520', 'spider_dev_521'], losses ['spider_dev_507', 'spider_dev_517']); BIRD 2/3/15 (wins ['bird_dev_1033', 'bird_dev_1038'], losses ['bird_dev_1020', 'bird_dev_1035', 'bird_dev_1039']); Spider2-lite 0/0/20 (wins —, losses —)
- **registry no-graph vs before no-graph**: Spider 3/1/16 (wins ['spider_dev_507', 'spider_dev_510', 'spider_dev_513'], losses ['spider_dev_521']); BIRD 1/3/16 (wins ['bird_dev_1035'], losses ['bird_dev_1033', 'bird_dev_1036', 'bird_dev_1038']); Spider2-lite 0/0/20 (wins —, losses —)

## Stage breakdown, adaptive `gpt5full` run (tokens / calls, all datasets)

| Stage | Tokens | Calls |
|---|---:|---:|
| `align` | 369,211 | 314 |
| `direct` | 183,899 | 182 |
| `generate` | 156,195 | 95 |
| `extract_final` | 152,015 | 221 |
| `difficulty` | 122,895 | 227 |
| `compose` | 102,262 | 46 |
| `gen_tests` | 99,982 | 86 |
| `plan` | 85,558 | 46 |
| `av_view` | 80,418 | 50 |
| `rewrite` | 73,850 | 227 |
| `decompose` | 68,826 | 36 |
| `revise` | 15,590 | 16 |
| `choose` | 5,356 | 7 |
| `embed` | 3,888 | 320 |
| `promote_describe` | 1,777 | 1 |
| `ablation_av_view` | 989 | 1 |
| `ablation_generate` | 631 | 1 |
