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
├── registries/
│   ├── seed/       # frozen pre-evaluation registries
│   └── grown/      # per-database registries grown question by question
├── catalogs/
│   └── tables/     # cached large-schema table descriptions
└── benchmarks/
    └── architecture/
        ├── runs/       # controlled architecture-ablation JSON
        ├── registries/grown/
        ├── figures/
        └── skill_exports/
```

## Conventions

- Prediction rows, summaries, logs, reports, and plots stay with their run family.
- Legacy backend dump files retain their historical filenames beside the corresponding run.
- Per-database SQLite `SkillRegistry` snapshots live under `registries/grown/<run>/`.
- Seed registries are reusable inputs under `registries/seed/<seed-tag>/`.
- Historical experiment folders under `benchmarks/` and `graphs/` preserve their original names; new runs do not write there.
- JSON is canonical for registry reload. Sibling Markdown files are human-readable skill cards.

The path policy is defined in [`../paths.py`](../paths.py). Most commands accept an explicit output override when artifacts must be stored on another disk.
