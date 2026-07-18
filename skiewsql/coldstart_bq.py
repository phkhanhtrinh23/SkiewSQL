"""
coldstart_bq.py — build frozen cold-start view graphs (config S) for the Spider2 `bq*`
BigQuery databases, BEFORE any test question is observed.

BigQuery port of coldstart.py: reuses the dialect-agnostic stages (schema analysis, candidate
-> ViewSpec, signature dedup, ordering) but generates BigQuery-Standard-SQL CTE bodies and
validates each candidate with a BigQuery DRY-RUN (scans 0 bytes = FREE) via BQClient.dry,
instead of SQLite execution.

Leakage-safe: sees only schema DDL (render_bq_schema) — never questions or gold SQL.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from skiewsql import sqlview
from skiewsql.core import ViewGraph, ViewSpec
from skiewsql.agents import CATEGORIES, CAT_HELP
from skiewsql.llm import LLM, extract_json, extract_code, USAGE
from skiewsql.coldstart import (analyse_schema, _to_spec, _signature, _order_candidates,
                                MAX_REPAIR)
from skiewsql.spider2bq import BQClient, render_bq_schema, load_bq_tasks
from skiewsql.bq_method import validate_bq_view

SEED_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_real", "seed_graphs")

BQ_RULES = (
    "Use backtick-quoted fully-qualified table names exactly as in the DDL "
    "(`project.dataset.table`). Handle nested/repeated fields with UNNEST, and date-sharded tables "
    "with wildcard tables + _TABLE_SUFFIX when appropriate. No trailing semicolons.")

GEN_SYS = (
    "You are a reusable BigQuery Standard SQL CTE generator building a database-specific library of "
    "reusable CTE definitions BEFORE any test question is observed. Generate reusable intermediate "
    "relations, NOT final-answer queries. Each candidate must be useful for MULTIPLE plausible "
    "future questions, have a clear row grain, use only existing tables/columns, preserve "
    "identifiers needed for later joins, expose useful descriptive+measure columns, be "
    "deterministic and executable BigQuery SQL, avoid arbitrary LIMIT, and avoid question-specific "
    "literals (a specific year/country/name/threshold/top-k). ORDER BY is allowed — use it inside "
    "OVER(...) for RANK/WIN views (expose a rank/running-total column so any Top-K is a downstream "
    "WHERE rank<=K); just never pair it with a fixed LIMIT. Acceptable STABLE filters: "
    "is_active/status='completed' when the schema documents it as a valid state, or selecting the "
    "latest version of a repeatedly-updated record. Do NOT force every category. " + BQ_RULES + " "
    "Alias pass-through columns to clean names matching the schema; only DERIVED columns (ratio, "
    "count, flag, rank, running total) get a new descriptive alias. Output strict JSON only."
)
GEN_USER = """BigQuery schema (DDL — AUTHORITATIVE for exact table/column names):
{schema}

Schema analysis (guidance: roles, grain, safe joins, supported categories):
{analysis}

Existing CTE library (avoid duplicating; you MAY build on them by selecting FROM them):
{existing}

Categories: {cat_help}

Generate at most {max_per_cat} candidate(s) per APPLICABLE category. For each candidate return the
CTE BODY as a single SELECT (NO `WITH`, NO trailing `;`) that could be placed inside `name AS ( ... )`.
If a candidate reads from another candidate, reference it by name in FROM and list it in `input_ctes`.
Keep intrinsic concept-defining filters inside `semantic_filters`; never bake a question-specific
literal into the body.

Return JSON:
{{
  "candidates": [
    {{"name": "snake_case_name", "category": "ONE OF {cats}",
      "description": "general NL description + when to use (for retrieval)",
      "sql": "SELECT ... (CTE body only, no WITH)",
      "input_tables": ["`project.dataset.table` ..."], "input_ctes": ["names_or_empty"],
      "output_columns": ["clean alias names"], "grain": ["key column alias(es), one row per"],
      "keys_preserved": ["..."], "semantic_filters": {{"column": "value"}},
      "potential_question_families": ["..."], "confidence": 0.0}}
  ],
  "unsupported_categories": [{{"category": "...", "reason": "..."}}]
}}"""


def generate_candidates_bq(llm, analysis, existing, schema, max_per_cat=2, tag="cs_bq_generate"):
    ex = "\n".join(f"- {v.name} ({v.category}): outputs {v.output_columns}; grain {v.grain}"
                   for v in existing) or "(empty)"
    user = GEN_USER.format(schema=schema[:14000], analysis=json.dumps(analysis)[:6000], existing=ex,
                           cat_help=CAT_HELP, cats="/".join(CATEGORIES), max_per_cat=max_per_cat)
    for budget in (6000, 9500):
        txt = llm.ask(GEN_SYS, user, tag=tag, max_tokens=budget)
        data = extract_json(txt) or {}
        cands = list(data.get("candidates", []) or [])
        if cands:
            return cands, list(data.get("unsupported_categories", []) or [])
    return [], []


REPAIR_SYS = ("You fix ONE reusable BigQuery CTE body so it compiles (dry-run valid) and exposes its "
              "declared output columns. " + BQ_RULES + " Return one corrected ```sql block (the CTE "
              "body only: a single SELECT, no WITH, no trailing ;).")
REPAIR_USER = """BigQuery schema (DDL):
{schema}

The CTE `{name}` (category {category}) must expose columns: {outs}
Its current body failed with: {error}
```sql
{body}
```
Return the corrected CTE body:
```sql
SELECT ...
```"""


def _repair_bq(llm, schema, spec, error, tag="cs_bq_repair"):
    txt = llm.ask(REPAIR_SYS, REPAIR_USER.format(schema=schema[:12000], name=spec.name,
                  category=spec.category, outs=spec.output_columns, error=error, body=spec.body_sql),
                  tag=tag, max_tokens=1200)
    out = extract_code(txt, langs=("sql", "cte"))
    return out.strip().rstrip(";") if out else None


def validate_and_register_bq(client, graph, llm, schema, candidates):
    specs = [s for s in (_to_spec(c) for c in candidates) if s is not None]
    specs = _order_candidates(specs)
    accepted, rejected = [], []
    seen_sigs = {_signature(v): v.name for v in graph.views.values()}
    for spec in specs:
        spec.depends_on = [d for d in spec.depends_on if graph.has(d)]
        sig = _signature(spec)
        if sig in seen_sigs:
            rejected.append({"name": spec.name, "reason": f"redundant with {seen_sigs[sig]}"})
            continue
        ok, msg, attempts = False, "", 0
        cur = spec
        for attempts in range(MAX_REPAIR + 1):
            graph.add_view(cur)
            ok, msg = validate_bq_view(client, graph, cur)        # FREE dry-run
            if ok:
                break
            graph.remove_view(cur.name)
            fixed = _repair_bq(llm, schema, cur, msg)
            if not fixed or fixed == cur.body_sql:
                break
            cur.body_sql = fixed
        if ok:
            sqlview.enforce_contract(cur, "bigquery")     # derive Φ/G from SQL (accurate guard)
            seen_sigs[sig] = cur.name
            rec = asdict(cur)
            rec["repair_attempts"] = attempts
            accepted.append(rec)
        else:
            rejected.append({"name": spec.name, "reason": f"validation failed: {msg}", "attempts": attempts})
    return accepted, rejected


def build_db_bq(llm, client, db_id, *, max_per_cat=2, rounds=1):
    schema = render_bq_schema(db_id)
    analysis = analyse_schema(llm, schema, profile="")           # leakage-safe: DDL only
    graph = ViewGraph(db_id=db_id)
    all_acc, all_rej = [], []
    for _r in range(max(1, rounds)):
        cands, _u = generate_candidates_bq(llm, analysis, list(graph.views.values()),
                                           schema=schema, max_per_cat=max_per_cat)
        acc, rej = validate_and_register_bq(client, graph, llm, schema, cands)
        all_acc += acc
        all_rej += rej
        if not acc:
            break
    from skiewsql.skillify import attach_skills                  # skillify: attach reuse contract
    attach_skills(llm, graph, dialect="BigQuery")
    cats = sorted({v.category for v in graph.views.values()})
    report = {"db_id": db_id, "n_accepted": len(all_acc), "n_rejected": len(all_rej),
              "categories_covered": cats, "accepted": all_acc, "rejected": all_rej,
              "depends_on_edges": graph.n_edges("DEPENDS_ON")}
    return graph, report


def main():
    ap = argparse.ArgumentParser(description="Build frozen BigQuery cold-start CTE graphs (config S).")
    ap.add_argument("--dbs", default="", help="comma list of bq db names; empty = all DBs with bq tasks")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--max_per_cat", type=int, default=2)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--tag", default="seedbq")
    args = ap.parse_args()

    if args.dbs.strip():
        dbs = [d.strip() for d in args.dbs.split(",") if d.strip()]
    else:
        import collections
        tasks = load_bq_tasks(10 ** 9)
        dbs = [db for db, _ in collections.Counter(t["db"] for t in tasks).most_common()]

    out_dir = os.path.join(SEED_ROOT, f"{args.tag}_bigquery")
    os.makedirs(out_dir, exist_ok=True)
    client = BQClient(max_gb=0.0)                                # dry-run only; never executes
    llm = LLM(model=args.model, temperature=0.0)
    USAGE.reset()
    print(f"Cold-start build (BigQuery) — {len(dbs)} DBs | model={args.model} "
          f"max_per_cat={args.max_per_cat}\n")
    summary = {}
    for db_id in dbs:
        tok0 = USAGE.total
        try:
            graph, report = build_db_bq(llm, client, db_id, max_per_cat=args.max_per_cat,
                                        rounds=args.rounds)
        except Exception as e:  # noqa: BLE001
            print(f"  [{db_id}] BUILD ERROR: {type(e).__name__}: {str(e)[:80]}", flush=True)
            continue
        report["build_tokens"] = USAGE.total - tok0
        sqlview.save_graph(graph, os.path.join(out_dir, f"{db_id}.json"))
        json.dump(report, open(os.path.join(out_dir, f"{db_id}.report.json"), "w"), indent=2)
        cats = ",".join(report["categories_covered"])
        summary[db_id] = {"views": graph.n_views(), "cats": cats}
        print(f"  [{db_id}] views={graph.n_views():2d} accepted={report['n_accepted']} "
              f"rejected={report['n_rejected']} cats={cats} tok={report['build_tokens']}", flush=True)
    json.dump(summary, open(os.path.join(out_dir, "_build_summary.json"), "w"), indent=2)
    tot = sum(v["views"] for v in summary.values())
    print(f"\nBuilt {tot} views across {len(summary)} DBs -> {out_dir}")


if __name__ == "__main__":
    main()
