# Per-database skill registry

SkiewSQL keeps one `SkillRegistry` for each database. The registry is a
mapping from skill name to `ViewSpec` plus lookup indexes. It is not a graph.
Dependencies are stored once in `ViewSpec.depends_on`.

## Stored data

The registry persists executable SQL and its contract: source tables, output
columns, grain, filters, dependencies, description, identity, version,
validation metadata, and reuse evidence. Executed result rows are transient
and are never written to the registry.

## Admission

A generated candidate is exploratory during the current question. It becomes
reusable only after the final answer succeeds and admission:

1. derives the contract from SQL and the live database;
2. executes the complete candidate and checks its assertions;
3. computes its SQL hash and stable skill ID;
4. rejects an incomplete or invalid contract;
5. deduplicates the accepted ViewSpec and updates the indexes.

A candidate containing several dependent CTEs is one validation unit. Partial
success is discarded.

## Retrieval

Retrieval follows the paper:

1. **Index:** intersect category, source-table, required-output, and grain
   postings. SQL hash supports identity and deduplication; the description
   index supports semantic ranking.
2. **Filter:** inspect each full ViewSpec and reject the wrong database,
   dialect, schema version, outputs, grain, filters, aggregation, joins, or
   dependencies.
3. **Rank:** combine description similarity, contract overlap, and earlier
   reuse evidence.
4. **Verify:** select a guaranteed semantic match or return NONE.

An index intersection only creates candidates. It never proves that a
candidate has the requested meaning.
