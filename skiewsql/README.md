# SkiewSQL package

See the repository [README](../README.md) for installation, dataset layout,
paper-aligned commands, registry semantics, and the end-to-end script.

The canonical implementation is:

- `core.py`: `ViewSpec` and the flat per-database `SkillRegistry`;
- `registry.py`: index, filter, rank, verify, and admission;
- `realrun.py`: the sequential question pipeline;
- `sqlview.py`: validation and registry persistence.
