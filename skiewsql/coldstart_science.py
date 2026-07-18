"""
coldstart_science.py — build frozen cold-start seed graphs for ScienceBenchmark databases on
PostgreSQL, so config S (seed then online growth) can run via science_method.

Reuses the proven SQLite cold-start pipeline (coldstart.analyse_schema / generate_candidates /
_to_spec / _order_candidates / _signature / _repair) but swaps the two dialect-bound stages:
schema rendering (science_method.render_pg_schema) and execution-grounded validation
(science_method.validate_view against the live Postgres DB). Contracts are re-derived with the
`postgres` sqlglot dialect. Output is byte-compatible with sqlview.load_graph, so science_method's
_init_graph loads it as the seed.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Dict, List, Tuple

from skiewsql import coldstart, sqlview, science_method
from skiewsql.core import ViewGraph
from skiewsql.llm import LLM, USAGE
from skiewsql.skillify import attach_skills

SEED_ROOT = coldstart.SEED_ROOT


def _validate_and_register_pg(client, graph: ViewGraph, llm, candidates: List[Dict], db: str):
    specs = [s for s in (coldstart._to_spec(c) for c in candidates) if s is not None]
    specs = coldstart._order_candidates(specs)
    accepted, rejected = [], []
    seen = {coldstart._signature(v): v.name for v in graph.views.values()}
    for spec in specs:
        spec.depends_on = [d for d in spec.depends_on if graph.has(d)]
        sig = coldstart._signature(spec)
        if sig in seen:
            rejected.append({"name": spec.name, "reason": f"redundant with {seen[sig]}"})
            continue
        ok, msg, cur = False, "", spec
        for _ in range(coldstart.MAX_REPAIR + 1):
            graph.add_view(cur)
            ok, msg = science_method.validate_view(client, graph, cur, db)
            if ok:
                break
            graph.remove_view(cur.name)
            fixed = coldstart._repair(llm, cur, list(graph.views.keys()), msg)
            if not fixed or fixed == cur.body_sql:
                break
            cur.body_sql = fixed
        if ok:
            sqlview.enforce_contract(cur, "postgres")
            seen[sig] = cur.name
            accepted.append(asdict(cur))
        else:
            rejected.append({"name": spec.name, "reason": f"validation failed: {msg}"})
    return accepted, rejected


def build_db(llm, client, db: str, max_per_cat: int = 2, rounds: int = 1):
    schema = science_method.render_pg_schema(client, db)
    analysis = coldstart.analyse_schema(llm, schema, profile="")     # no SQLite PRAGMA profile on PG
    graph = ViewGraph(db_id=db)
    all_acc, all_rej = [], []
    for _r in range(max(1, rounds)):
        cands, _unsupported = coldstart.generate_candidates(
            llm, analysis, list(graph.views.values()), schema=schema, max_per_cat=max_per_cat)
        acc, rej = _validate_and_register_pg(client, graph, llm, cands, db)
        all_acc += acc
        all_rej += rej
        if not acc:
            break
    attach_skills(llm, graph, dialect="PostgreSQL")
    report = {"db_id": db, "n_accepted": len(all_acc), "n_rejected": len(all_rej),
              "categories": sorted({v.category for v in graph.views.values()}),
              "accepted": all_acc, "rejected": all_rej}
    return graph, report


def main():
    ap = argparse.ArgumentParser(description="Build cold-start seed graphs for ScienceBench (Postgres).")
    ap.add_argument("--dbs", default="cordis", help="comma list: cordis,oncomx,sdss")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--max_per_cat", type=int, default=2)
    ap.add_argument("--tag", default="sciseed")
    args = ap.parse_args()
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()]

    out_dir = os.path.join(SEED_ROOT, f"{args.tag}_science")
    os.makedirs(out_dir, exist_ok=True)
    client = science_method.PGClient()
    llm = LLM(model=args.model, temperature=0.0)
    USAGE.reset()
    print(f"Cold-start (Postgres) — dbs={dbs} model={args.model} max_per_cat={args.max_per_cat}")
    summary = {}
    for db in dbs:
        graph, report = build_db(llm, client, db, max_per_cat=args.max_per_cat)
        seed_path = os.path.join(out_dir, f"{db}.json")
        sqlview.save_graph(graph, seed_path)
        json.dump(report, open(os.path.join(out_dir, f"{db}.report.json"), "w"), indent=2)
        summary[db] = {"views": graph.n_views(), "accepted": report["n_accepted"],
                       "rejected": report["n_rejected"], "cats": report["categories"]}
        print(f"  [{db}] views={graph.n_views()} accepted={report['n_accepted']} "
              f"rejected={report['n_rejected']} cats={','.join(report['categories'])}")
    json.dump(summary, open(os.path.join(out_dir, "_summary.json"), "w"), indent=2)
    client.close()
    print(f"\nSeed graphs -> {out_dir}/  (load with science_method --seed_dir {out_dir})")


if __name__ == "__main__":
    main()
