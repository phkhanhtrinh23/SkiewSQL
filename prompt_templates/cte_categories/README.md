# Reusable Agent-View Taxonomy (CTE Knowledge Memory)

Pre-built, schema-grounded agent views (CTEs) for AV-SQL. Each view is a node in a
**view dependency graph** `G = (V, E)`: a node is one validated CTE; an edge `u -> v`
means view `v` is built on top of view `u` (`depends_on`). Built once per database
*before* evaluation, then queried at question time with **retrieve-or-generate**:

```
rewrite(Q) -> steps s_1..s_k
for each step s_i:
    v = retrieve(G, s_i)              # embedding + category + table signature match
    if sim(v, s_i) < tau:            # cache miss
        v = generate(s_i)            # category template below (standard AV-SQL view gen)
        G.add(v)                     # persist for future questions
compose(v_1..v_k) -> final SQL       # planner / generator / revisor
```

## Category names (use these in the paper)

| # | Formal name (paper)        | Code     | Operator basis              | Builds                                              | (was)            |
|---|----------------------------|----------|-----------------------------|-----------------------------------------------------|------------------|
| 1 | **Selection View**         | `SEL`    | selection σ                 | predicate / temporal row subset (a cohort)          | Filter/Cohort    |
| 2 | **Normalization View**     | `NORM`   | projection π + cleaning     | type casts, NULL handling, value canonicalization   | Clean/Normalize  |
| 3 | **Aggregation View**       | `AGG`    | grouping γ                  | grouped measures per key (rollups)                  | Aggregate/Rollup |
| 4 | **Join–Enrichment View**   | `JOIN`   | join ⋈                      | denormalized wide relation across tables            | Join/Enrich      |
| 5 | **Ranking–Dedup View**     | `RANK`   | partitioned window rank     | ROW_NUMBER/RANK: latest-per-key, top-k, dedup       | Rank/Top-N/Dedup |
| 6 | **Temporal Window View**   | `WIN`    | ordered analytic window     | running totals, moving avg, LAG/LEAD deltas         | Window/Trend     |
| 7 | **Reshaping View**         | `RESHAPE`| pivot / unpivot             | conditional aggregation, long↔wide                  | Pivot/Reshape    |
| 8 | **Recursive Traversal View**| `REC`   | recursive CTE (fixpoint)    | hierarchy / graph paths (org chart, tree, BOM)      | Recursive/Hierarchy |
| 9 | **Set-Algebra View**       | `SET`    | union ∪ / intersect ∩ / except − | cohort combination / difference               | Set-op cohort    |
| 10| **Semantic Domain View**   | `SEM`    | derived-metric / business rule | external-knowledge concept (e.g. `churned`, `fiscal_quarter`) | Domain-rule |

`SEL–JOIN` are **schema-generic** (mineable from any DB, max reuse). `WIN`, `RANK`,
`RESHAPE`, `REC` are **structure-driven** (need a time column / partition key / hierarchy
FK). `SEM` is **domain-specific** (needs external knowledge / docs).

## Graph-node metadata (emitted with every view)

```json
{
  "view_name": "snake_case_name",
  "category": "SEL|NORM|AGG|JOIN|RANK|WIN|RESHAPE|REC|SET|SEM",
  "source_tables": ["table_a", "table_b"],
  "output_columns": [{"name": "col", "type": "INT", "role": "key|dim|measure|flag"}],
  "grain": "one row per <entity / entity×period>",
  "parameters": [{"name": "{{status}}", "type": "TEXT", "default": "'active'"}],
  "depends_on": ["other_view_name"],          // graph edges (composability)
  "description": "NL summary used for retrieval / embedding",
  "reuse_scope": "schema-generic | structure-driven | domain-specific"
}
```

`{SHARED_RULES}` in each template is replaced at load time by `_shared.txt`.
