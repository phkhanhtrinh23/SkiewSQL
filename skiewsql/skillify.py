"""
skillify.py — turn a validated ViewSpec (a CTE in the seed graph) into a full reusable SKILL
document: name, description, SQL, when-to-use, when-NOT-to-use, output schema, notation
(grounded columns/metric/grain), composition (cardinality-safe joins), comparison to sibling
views, and cross-dialect notes.

This upgrades a thin ViewSpec (SQL + tags) into a self-describing, self-disambiguating,
portable skill — the artifact the reuse selector needs to (a) avoid negative reuse via the
when-NOT-to-use section, (b) join safely via the composition section, and (c) port across
SQLite/Snowflake/BigQuery via the dialect notes.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List

from skiewsql.llm import LLM

SKILL_SYS = (
    "You write a REUSABLE SQL VIEW SKILL document for a Text-to-SQL system. Given one validated "
    "view (its SQL body) plus the sibling views in the same database, produce a precise skill that "
    "tells a downstream agent exactly WHEN to reuse this view, WHEN NOT TO (the anti-patterns that "
    "cause silently-wrong SQL: wrong grain, wrong cohort/filter, wrong aggregation, mis-counting), "
    "how to COMPOSE it safely (which joins do NOT duplicate its measures and why, by cardinality), "
    "how it COMPARES to sibling views (use X instead when...), and how its SQL differs across "
    "Snowflake/PostgreSQL, BigQuery, and SQLite dialects. Be concrete and grounded ONLY in the "
    "given SQL and schema — do not invent columns. Output the skill as clean Markdown with the "
    "exact section headers requested.")

SKILL_USER = """Database dialect of the source SQL: {dialect}

Schema (DDL):
{schema}

THIS VIEW to skillify:
- name: {name}   category: {category}
- grain: {grain}   outputs: {outputs}
- SQL body:
{body}

Sibling views in this database (for the Comparison section — reference by name):
{siblings}

Write the skill with EXACTLY these Markdown sections, in this order:
# {name}
(one-line description of what questions it answers)
## SQL view
(the view body, as given, in a ```sql block)
## When to use
(bullet list of concrete question types / good matches / things it can be composed into)
## Output schema
(each exposed column: name — meaning + which base column/metric it derives from)
## Notation
(Grounded columns: table.column list; Metric: definitions; Key and grain: the grain tuple)
## Composition
(which sibling/dim to join on which key; state explicitly WHY the join is cardinality-safe —
i.e. does not duplicate this view's measures — and give one example query)
## Dialect notes
(show the key dialect-sensitive expressions — date truncation, etc. — for Snowflake/PostgreSQL,
BigQuery, and SQLite)
"""


STRUCT_SYS = (
    "You write the FULL machine-usable SKILL for a validated SQL view — an ENABLING contract that "
    "helps a downstream agent reuse this view and COMPOSE more SQL on top of it. Ground ONLY in the "
    "given SQL/schema; do not invent columns. Cover: what it answers, the question types it serves, "
    "each output column's meaning + source, the grounded base columns and metric definitions, and "
    "cardinality-safe composition (which joins do NOT duplicate its measures and why, so the planner "
    "can build on it correctly). Output strict JSON only.")
STRUCT_USER = """View `{name}` ({category}), grain {grain}, outputs {outputs}
SQL:
{body}

Sibling views (same DB): {siblings}

Return JSON with EVERY field populated:
{{"description": "one line: what questions this view answers",
  "when_to_use": ["concrete question type this view correctly answers or can be composed into", ...],
  "output_schema": ["col_name: meaning + which base column/metric it derives from", ...],
  "grounded_columns": ["table.column actually referenced in the SQL", ...],
  "metric": ["derived_col = <aggregate/expression definition>", ...],
  "composition": ["cardinality-SAFE join guidance: join to <dim/view> on <key> — safe because it is one-row-per-<key> so this view's measures are NOT duplicated; do NOT join to <one-to-many table/view> without re-aggregating first, because it would multiply this view's rows/measures", ...]}}"""


def skillify_struct(llm: LLM, view: Dict, siblings: List[Dict], dialect: str = "SQLite") -> Dict[str, str]:
    """Return the FULL skill as flat strings (for ViewSpec.params): description, when_to_use,
    when_not_to_use, output_schema, grounded_columns, metric, composition, comparison. These are
    injected into the reuse selector (when-not/comparison/schema/notation) and the planner
    (composition/notation)."""
    from skiewsql.llm import extract_json
    sib = ", ".join(f"{v['name']}({v['category']})" for v in siblings) or "(none)"
    txt = llm.ask(STRUCT_SYS, STRUCT_USER.format(
        name=view["name"], category=view["category"], grain=view.get("grain"),
        outputs=view.get("output_columns"), body=view["body_sql"][:1400], siblings=sib),
        tag="skillify_struct", max_tokens=1600)
    d = extract_json(txt) or {}
    def _join(k):
        v = d.get(k) or []
        return " | ".join(str(x) for x in v) if isinstance(v, list) else str(v)
    return {"description": _join("description"), "when_to_use": _join("when_to_use"),
            "output_schema": _join("output_schema"), "grounded_columns": _join("grounded_columns"),
            "metric": _join("metric"), "composition": _join("composition")}


def attach_skills(llm: LLM, graph, dialect: str = "SQLite") -> int:
    """Skillify every view in a graph IN PLACE: store when_to_use / when_not_to_use / comparison
    into each ViewSpec.params so the reuse selector can consume the contract. Run after a DB's
    views are all built (so siblings exist). Returns number of views skillified."""
    views = list(graph.views.values())
    dicts = [{"name": v.name, "category": v.category, "grain": v.grain,
              "output_columns": v.output_columns, "body_sql": v.body_sql} for v in views]
    for i, v in enumerate(views):
        sibs = [dicts[j] for j in range(len(dicts)) if j != i]
        try:
            v.params.update(skillify_struct(llm, dicts[i], sibs, dialect))
        except Exception:  # noqa: BLE001 — a skill failure must not drop the view
            continue
    return len(views)


def skillify(llm: LLM, view: Dict, siblings: List[Dict], schema: str, dialect: str) -> str:
    sib = "\n".join(f"- {v['name']} ({v['category']}): {v.get('description','')[:90]} "
                    f"| outputs {v.get('output_columns')}" for v in siblings) or "(none)"
    return llm.ask(SKILL_SYS, SKILL_USER.format(
        dialect=dialect, schema=schema[:6000], name=view["name"], category=view["category"],
        grain=view.get("grain"), outputs=view.get("output_columns"),
        body="```sql\n" + view["body_sql"] + "\n```", siblings=sib),
        tag="skillify", max_tokens=2200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed_graph", required=True, help="path to a {db}.json seed graph")
    ap.add_argument("--view", default="", help="view name to skillify (default: first AGG/JOIN)")
    ap.add_argument("--dialect", default="SQLite")
    ap.add_argument("--schema", default="", help="optional schema DDL text file")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    g = json.load(open(args.seed_graph))
    views = g["views"]
    target = next((v for v in views if v["name"] == args.view), None) if args.view else \
        next((v for v in views if v["category"] in ("AGG", "JOIN")), views[0])
    siblings = [v for v in views if v["name"] != target["name"]]
    schema = open(args.schema).read() if args.schema and os.path.exists(args.schema) else \
        "(schema not supplied; ground only in the view SQL)"
    llm = LLM(model=args.model, temperature=0.0)
    md = skillify(llm, target, siblings, schema, args.dialect)
    out = args.out or os.path.join(os.path.dirname(args.seed_graph),
                                   f"SKILL_{target['name']}.md")
    open(out, "w").write(md)
    print(md)
    print(f"\n---\nwrote {out}")


if __name__ == "__main__":
    main()
