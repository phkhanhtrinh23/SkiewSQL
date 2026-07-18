"""
bq_method.py — run the SkiewSQL view-memory method (retrieve-or-generate reusable CTEs) WITH the
Layer 3 adversarial verifier, natively on BigQuery, staying inside the 1 TiB/month free tier.

Cost discipline:
  * CTE validation uses BigQuery DRY-RUN only (scans 0 bytes = FREE): it confirms the CTE is valid
    BigQuery SQL and exposes the declared output columns, which is all `validate_view` needs.
  * Only the FINAL composed query per question is actually executed (cost-guarded + a sleep between
    executions to be gentle on quota / rate limits).

Reuses: core.ViewGraph / ViewSpec / ViewRequest / compose_sql, sqlview.retrieve, agents (rewrite,
propose_views, planner, verify_reuse), and BQClient / render_bq_schema / load_bq_tasks / score from
spider2bq. Generation of executable SQL (view bodies + final query) is BigQuery-dialect here.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict, List, Optional, Tuple

from skiewsql import agents, sqlview
from skiewsql.core import ViewGraph, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE
from skiewsql.spider2bq import (BQClient, render_bq_schema, load_bq_tasks, score, _evidence,
                                PRICE_PER_TB)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "skiewsql", "results_real")


# --------------------------------------------------------------------------- #
# BigQuery-dialect generation (view body, final query, repair)
# --------------------------------------------------------------------------- #
VIEW_SYS = (
    "You build ONE reusable BigQuery Standard SQL CTE body: a single SELECT (no `WITH` wrapper, no "
    "trailing `;`) that defines the view. Use backtick-quoted fully-qualified table names exactly as "
    "in the DDL, UNNEST for nested/repeated fields, and wildcard tables + _TABLE_SUFFIX for "
    "date-sharded tables. Carry key/id columns into the output so the view stays joinable. Lift "
    "question-specific literals OUT of the view. Output one ```sql block then one ```json metadata block.")
VIEW_USER = """BigQuery schema (DDL):
{schema}

Build the view `{name}` (category {category}). Meaning: {desc}
Required output columns (alias EXACTLY to these): {outs}
Grain (one row per): {grain}
{existing}{error}
```sql
SELECT ...
```
```json
{{"output_columns": ["..."], "source_tables": ["..."], "grain": ["..."], "depends_on": []}}
```"""

FINAL_SYS = (
    "You are the BigQuery SQL generator. The listed views are ALREADY DEFINED as CTEs (do not "
    "redefine them). Write ONLY the final SELECT answering the question, using those views and, if "
    "needed, base tables (backtick-quoted). Apply the question-specific filters/ordering/limit here. "
    "Output one ```sql block.")
FINAL_USER = """BigQuery schema:
{schema}

Already-defined CTE views you can SELECT FROM (do NOT redefine):
{views}

Question: {question}
{evidence}
Plan:
{plan}
```sql
SELECT ...
```"""

DIRECT_SYS = ("You are a BigQuery Standard SQL generator. Output one ```sql block with a single "
              "executable BigQuery query (backtick-quoted fully-qualified tables). No explanation.")
DIRECT_USER = """BigQuery schema (DDL):
{schema}

Question: {question}
{evidence}{error}
```sql
SELECT ...
```"""


def gen_bq_view(llm, schema, req, existing) -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = ("You MAY build on these existing views (SELECT FROM them, list in depends_on):\n"
              + "\n".join(f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]) + "\n")
    txt = llm.ask(VIEW_SYS, VIEW_USER.format(schema=schema[:14000], name=req.want_name,
                  category=req.category, desc=req.text, outs=req.required_outputs,
                  grain=req.required_grain, existing=ex, error=""), tag="bq_view", max_tokens=1400)
    body = extract_code(txt, langs=("sql", "cte"))
    meta = extract_json(txt) or {}
    if not body:
        return None
    outs = [str(x) for x in (meta.get("output_columns") or req.required_outputs)]
    low = {o.lower() for o in outs}
    for r in req.required_outputs:
        if r.lower() not in low:
            outs.append(r)
    deps = [str(d) for d in (meta.get("depends_on") or []) if any(d == v.name for v in existing)]
    return ViewSpec(name=req.want_name, category=req.category, body_sql=body.strip().rstrip(";"),
                    source_tables=[str(x) for x in (meta.get("source_tables") or [])],
                    output_columns=outs, grain=[str(x) for x in (meta.get("grain") or req.required_grain)],
                    semantic_filters={str(k): str(v) for k, v in (req.required_filters or {}).items()},
                    depends_on=deps, description=req.text)


def compose_bq_final(llm, schema, question, evidence, chosen, plan) -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}" for v in chosen)
    txt = llm.ask(FINAL_SYS, FINAL_USER.format(schema=schema[:12000], views=vs, question=question,
                  evidence=evidence, plan=plan), tag="bq_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def gen_bq_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema[:14000], question=question,
                  evidence=evidence, error=err), tag="bq_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


# --------------------------------------------------------------------------- #
# FREE dry-run validation of a generated CTE against BigQuery
# --------------------------------------------------------------------------- #
def validate_bq_view(client: BQClient, graph: ViewGraph, spec: ViewSpec) -> Tuple[bool, str]:
    try:
        dep_specs = graph.topo_closure(spec.depends_on) if spec.depends_on else []
        chosen = {s.name: s for s in dep_specs}
        chosen[spec.name] = spec
        ordered = sqlview._order_specs(list(chosen.values()))
        with_clause = ",\n".join(s.cte_clause() for s in ordered)
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {with_clause}\nSELECT * FROM {spec.name} LIMIT 5"
        ok, err, cols, _gb = client.dry(sql)              # FREE
        if not ok:
            return False, err
        low = {c.lower() for c in cols}
        missing = [c for c in spec.output_columns if c.lower() not in low]
        return (not missing), ("ok" if not missing else f"declared outputs missing: {missing}")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------- #
# The method loop (online view memory + Layer-3 verify) on BigQuery
# --------------------------------------------------------------------------- #
def _save(tag, rows, client, verify, graphs=None):
    out = os.path.join(RESULTS_DIR, f"{tag}_bq_method.json")
    json.dump({"verify": verify, "rows": rows, "n_ok": sum(r["correct"] for r in rows),
               "reuse": sum(r["reused"] for r in rows), "gen": sum(r["generated"] for r in rows),
               "bq_cost_usd": client.cost_usd, "bq_gb": client.bytes_billed / 1e9,
               "llm_usage": USAGE.snapshot()}, open(out, "w"), indent=2)
    # dump the grown per-DB graphs (CTE bodies + validated_on/counter_examples learned this run)
    if graphs:
        from dataclasses import asdict
        gdump = {db: {"views": {n: asdict(v) for n, v in g.views.items()}, "n_views": g.n_views()}
                 for db, g in graphs.items()}
        json.dump(gdump, open(os.path.join(RESULTS_DIR, f"{tag}_bq_graphs.json"), "w"), indent=2)
    return out


def _init_graph(db, seed_dir):
    """Config S: load frozen cold-start seed graph if present, else empty (config A)."""
    if seed_dir:
        sp = os.path.join(seed_dir, f"{db}.json")
        if os.path.exists(sp):
            g = sqlview.load_graph(sp)
            return g, set(g.views.keys())
    return ViewGraph(db_id=db), set()


def run(n, dbs, verify, sleep, max_gb, max_views, model, tag, budget_tib=0.5, seed_dir=""):
    tasks = load_bq_tasks(n, dbs)
    client = BQClient(max_gb=max_gb)
    llm = LLM(model=model)
    emb = Embedder()
    graphs: Dict[str, ViewGraph] = {}
    seed_names: Dict[str, set] = {}
    rows = []
    cfg = "S(seed)" if seed_dir else ("A" if verify > 0 else "B")
    print(f"BQ method run [{cfg}]: {len(tasks)} tasks | verify={verify} guard={max_gb}GB "
          f"budget={budget_tib}TiB seed_dir={seed_dir or '-'}\n")
    for ti, t in enumerate(tasks):
        if client.bytes_billed / 1e12 > budget_tib:      # cumulative free-tier safety cap
            print(f"  STOP: cumulative {client.bytes_billed/1e12:.3f} TiB > budget {budget_tib} TiB")
            break
        if ti and ti % 20 == 0:                          # periodic checkpoint
            _save(tag, rows, client, verify, graphs)
        db = t["db"]
        schema = render_bq_schema(db)
        ev = _evidence(t)
        # Memory scoping: config B (verify==0) RESETS the graph per question (faithful AV-SQL, no
        # cross-question memory); config A/S (verify>0) PERSIST; config S also LOADS a seed graph.
        if verify <= 0:
            graphs[db] = ViewGraph(db_id=db)
        elif db not in graphs:
            graphs[db], seed_names[db] = _init_graph(db, seed_dir)
        g = graphs.setdefault(db, ViewGraph(db_id=db))
        sn = seed_names.get(db, set())
        _rw, rw = agents.rewrite_question(llm, schema, t["question"], ev)
        reqs, _raw, _sel = agents.propose_views(llm, schema, rw, max_views=max_views)

        chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
        reused_names = []                                # views reused this question (Layer-4 learning)
        for req in reqs:
            spec = None
            if verify > 0:                                        # only config A/S reuse
                spec, _d = sqlview.retrieve(g, req, emb, tau=0.55)
                if spec is not None:                              # Layer 3 gate
                    allows = sum(int(agents.verify_reuse(llm, spec, req)[0]) for _ in range(verify))
                    if allows * 2 < verify:
                        spec, vrej = None, vrej + 1
            if spec is not None:
                if spec.name in sn:
                    seed_reused += 1
                chosen.append(spec)
                reused += 1
                reused_names.append(spec.name)
                continue
            cand = gen_bq_view(llm, schema, req, list(g.views.values()))
            if cand is None:
                continue
            if g.has(cand.name):
                cand.name = f"{cand.name}_{len(g.views)}"
            g.add_view(cand)
            ok, _msg = validate_bq_view(client, g, cand)          # FREE dry-run
            if ok:
                chosen.append(cand)
                gen += 1
            else:
                g.remove_view(cand.name)

        # compose final query
        composed = None
        if chosen:
            plan = agents.planner(llm, schema, rw, chosen)
            final = compose_bq_final(llm, schema, t["question"], ev, chosen, plan)
            if final:
                try:
                    composed = compose_sql(g, [v.name for v in chosen], final)
                except Exception:  # noqa: BLE001
                    composed = None
        if composed is None:
            composed = gen_bq_direct(llm, schema, t["question"], ev)

        # execute (cost-guarded + sleep) with a small repair loop
        df, err = None, "no sql"
        for attempt in range(3):
            if not composed:
                break
            try:
                df = client.run(composed, sleep_s=sleep)
                err = ""
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                if attempt < 2:
                    composed = gen_bq_direct(llm, schema, t["question"], ev, prior_error=err) or composed
        correct, serr = (score(client, df, t) if df is not None else (False, err))
        # Layer 4: learn each reused view's boundary (correct reuse -> validated_on; wrong -> counter
        # _example). Mirrors realrun.py:346-354; grown graph persisted via _save's asdict dump.
        for nm in reused_names:
            v = g.views.get(nm)
            if v is None:
                continue
            if bool(correct) and t["question"] not in v.validated_on:
                v.validated_on = (v.validated_on + [t["question"]])[-10:]
            elif (not bool(correct)) and t["question"] not in v.counter_examples:
                v.counter_examples = (v.counter_examples + [t["question"]])[-10:]
        rows.append({"instance_id": t["instance_id"], "db": db, "correct": bool(correct),
                     "reused": reused, "seed_reused": seed_reused, "generated": gen,
                     "verify_reject": vrej, "graph_views": g.n_views(), "seed_views": len(sn),
                     "pred_sql": composed, "error": err or serr})
        print(f"  {t['instance_id']:8} {db:14} ok={int(correct)} reuse={reused}(seed={seed_reused}) "
              f"gen={gen} vrej={vrej} graph={g.n_views()} cost=${client.cost_usd:.4f} "
              f"{('' if correct else (err or serr)[:44])}", flush=True)

    n_ok = sum(r["correct"] for r in rows)
    tot_reuse = sum(r["reused"] for r in rows)
    tot_gen = sum(r["generated"] for r in rows)
    print(f"\n=== BQ method summary (verify={verify}) ===")
    print(f"  tasks {len(rows)} | correct {n_ok} ({100*n_ok/max(1,len(rows)):.1f}%) | "
          f"reuse {tot_reuse} | gen {tot_gen} | verify_rejects {sum(r['verify_reject'] for r in rows)}")
    print(f"  BigQuery executed {client.n_run} queries | scanned {client.bytes_billed/1e9:.2f} GB "
          f"| cost ${client.cost_usd:.4f} (free-tier: this counts toward 1 TiB/month)")
    out = _save(tag, rows, client, verify, graphs)    # dumps method json + grown graphs
    print(f"  wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--dbs", default="")
    ap.add_argument("--verify", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--max_gb", type=float, default=2.0)
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="bqm")
    ap.add_argument("--budget_tib", type=float, default=0.5, help="cumulative scan cap (TiB)")
    ap.add_argument("--seed_dir", default="", help="config S: dir of frozen seed graphs ({db}.json)")
    args = ap.parse_args()
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    run(args.n, dbs, args.verify, args.sleep, args.max_gb, args.max_views, args.model, args.tag,
        budget_tib=args.budget_tib, seed_dir=args.seed_dir)


if __name__ == "__main__":
    main()
