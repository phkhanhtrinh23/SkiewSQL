# Experiment artifact layout

`results_real` contains generated experiment evidence. New runners must write through the constants in `skiewsql.paths`. Do not place run files directly in this directory.

```text
results_real/
├── runs/
│   ├── sqlite/{spider,bird,spider2lite,sqlflow_spider}/
│   ├── beaver/
│   ├── bigquery/
│   ├── snowflake/
│   ├── livesql/
│   └── science/
├── graphs/
│   ├── seed/       # frozen pre-evaluation skill graphs
│   └── grown/      # SQLite graphs grown question by question
├── catalogs/
│   └── tables/     # cached large-schema table descriptions
└── benchmarks/
    └── architecture/
        ├── runs/       # controlled architecture-ablation JSON
        ├── graphs/grown/
        ├── figures/
        └── skill_exports/
```

## Conventions

- Prediction rows, summaries, logs, reports, and plots stay with their run family.
- Backend graph-dump files (`*_bq_graphs.json`, `*_sf_graphs.json`, and `*_beaver_graphs.json`) stay beside the corresponding backend run because they are single-file run snapshots.
- Per-database SQLite `ViewGraph` snapshots live under `graphs/grown/<run>/`.
- Seed graphs are reusable inputs and therefore live separately under `graphs/seed/<seed-tag>/`.
- A self-contained benchmark may keep its own `runs`, `graphs`, and `figures`, as the architecture benchmark does.
- JSON is canonical for graph reload. Sibling Markdown graph files are human-readable exports.

The path policy is defined in [`../paths.py`](../paths.py). Most commands accept an explicit output override when artifacts must be stored on another disk.
