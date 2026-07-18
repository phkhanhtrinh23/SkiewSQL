"""
sf_method.py — run the SkiewSQL view-memory method (retrieve-or-generate reusable CTEs) WITH the
optional Layer 3 adversarial verifier, natively on Snowflake, for the Spider 2.0-lite `sf*` tasks.

Direct port of bq_method.py to the Snowflake backend:
  * CTE validation uses `cursor.describe()` (compilation only, NO execution, no warehouse time —
    the exact analogue of the FREE BigQuery dry-run): it confirms the CTE is valid Snowflake SQL
    and exposes the declared output columns, which is all validation needs.
  * Only the FINAL composed query per question is actually executed (statement-timeout guarded,
    with a sleep between executions to be gentle on the shared participant warehouse).

Reuses: core.ViewGraph / ViewSpec / ViewRequest / compose_sql, sqlview.retrieve, agents (rewrite,
propose_views, planner, verify_reuse), and SFClient / render_sf_schema / load_sf_tasks / score
from spider2sf. Generation of executable SQL (view bodies + final query) is Snowflake-dialect here.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from typing import Dict, List, Optional, Tuple

from skiewsql import agents, sqlview
from skiewsql.core import ViewGraph, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE
from skiewsql.spider2sf import (SFClient, render_sf_schema, load_sf_tasks, score, _evidence)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_real")

SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max (matches realrun.py)

SF_RULES = (
    "Use fully-qualified table names DATABASE.SCHEMA.TABLE exactly as given in the schema "
    "headers. CRITICAL QUOTING RULES: base-table column identifiers are lowercase and "
    "case-sensitive — double-quote them exactly as in the DDL (e.g. \"block_timestamp\") EVERY "
    "time you touch the base table. Whenever a CTE/subquery selects a base column, ALIAS it to "
    "an unquoted name (e.g. SELECT \"country_code\" AS country_code) and refer ONLY to that "
    "unquoted alias downstream — never reference a quoted-lowercase name without quotes. For "
    "VARIANT columns use : path access and LATERAL FLATTEN. No backticks."
)

# --------------------------------------------------------------------------- #
# Snowflake-dialect generation (view body, final query, direct, repair)
# --------------------------------------------------------------------------- #
VIEW_SYS = (
    "You build ONE reusable Snowflake SQL CTE body: a single SELECT (no `WITH` wrapper, no "
    "trailing `;`) that defines the view. " + SF_RULES + " Carry key/id columns into the output "
    "so the view stays joinable. Lift question-specific literals OUT of the view. Output one "
    "```sql block then one ```json metadata block.")
VIEW_USER = """Snowflake schema (DDL):
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
    "You are the Snowflake SQL generator. The listed views are ALREADY DEFINED as CTEs (do not "
    "redefine them). Write ONLY the final SELECT answering the question, using those views and, "
    "if needed, base tables. " + SF_RULES + " Apply the question-specific filters/ordering/limit "
    "here. Output one ```sql block.")
FINAL_USER = """Snowflake schema:
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

DIRECT_SYS = ("You are a Snowflake SQL generator. Output one ```sql block with a single "
              "executable Snowflake query. " + SF_RULES + " No explanation.")
DIRECT_USER = """Snowflake schema (DDL):
{schema}

Question: {question}
{evidence}{error}
```sql
SELECT ...
```"""


def gen_sf_view(llm, schema, req, existing) -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = ("You MAY build on these existing views (SELECT FROM them, list in depends_on):\n"
              + "\n".join(f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]) + "\n")
    txt = llm.ask(VIEW_SYS, VIEW_USER.format(schema=schema[:14000], name=req.want_name,
                  category=req.category, desc=req.text, outs=req.required_outputs,
                  grain=req.required_grain, existing=ex, error=""), tag="sf_view", max_tokens=1400)
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


def compose_sf_final(llm, schema, question, evidence, chosen, plan) -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}" for v in chosen)
    txt = llm.ask(FINAL_SYS, FINAL_USER.format(schema=schema[:12000], views=vs, question=question,
                  evidence=evidence, plan=plan), tag="sf_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def gen_sf_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema[:14000], question=question,
                  evidence=evidence, error=err), tag="sf_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


# --------------------------------------------------------------------------- #
# AV-SQL Stage 3 — execution-repair (revisor) + semantic revisor, Snowflake dialect.
# These mirror agents.revise_sql / agents.semantic_revise verbatim in ROLE (the config-B
# baseline must be a faithful AV-SQL), specialised only for Snowflake dialect + quoting.
# --------------------------------------------------------------------------- #
REVISE_SYS = ("You are the SQL revisor. Fix the Snowflake query so it executes and answers the "
              "question. " + SF_RULES + " Output one corrected ```sql block only.")
REVISE_USER = """Snowflake schema (DDL):
{schema}

Question: {question}
{evidence}
This query failed or may be wrong:
```sql
{sql}
```
Error / issue: {error}

Return the corrected single query:
```sql
SELECT ...
```"""

SEM_SYS = ("You are the Revisor performing a final semantic check on a Snowflake query. Given a "
           "query that already executes, verify it truly answers the intent (correct columns, "
           "filters, aggregation, ordering/limit). If correct, return it unchanged; otherwise "
           "return a corrected query. " + SF_RULES + " Output one ```sql block only.")
SEM_USER = """Snowflake schema (DDL):
{schema}

Rewritten question:
{rewrite}
Original question: {question}
{evidence}

Current query and a preview of its result:
```sql
{sql}
```
Result preview (first rows): {preview}

Return the verified/corrected single query:
```sql
SELECT ...
```"""


def revise_sf_sql(llm, schema, question, evidence, sql, error) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(REVISE_SYS, REVISE_USER.format(schema=schema[:14000], question=question,
                  evidence=ev, sql=sql, error=error), tag="sf_revise", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


def semantic_revise_sf(llm, schema, rewrite_text, question, evidence, sql, preview) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(SEM_SYS, SEM_USER.format(schema=schema[:12000], rewrite=rewrite_text,
                  question=question, evidence=ev, sql=sql, preview=preview),
                  tag="sf_semantic", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


# --------------------------------------------------------------------------- #
# FREE describe-based validation of a generated CTE against Snowflake
# --------------------------------------------------------------------------- #
def validate_sf_view(client: SFClient, graph: ViewGraph, spec: ViewSpec) -> Tuple[bool, str]:
    try:
        dep_specs = graph.topo_closure(spec.depends_on) if spec.depends_on else []
        chosen = {s.name: s for s in dep_specs}
        chosen[spec.name] = spec
        ordered = sqlview._order_specs(list(chosen.values()))
        with_clause = ",\n".join(s.cte_clause() for s in ordered)
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {with_clause}\nSELECT * FROM {spec.name} LIMIT 5"
        ok, err, cols = client.describe(sql)              # FREE (compilation only)
        if not ok:
            return False, err
        low = {c.lower() for c in cols}
        missing = [c for c in spec.output_columns if c.lower() not in low]
        return (not missing), ("ok" if not missing else f"declared outputs missing: {missing}")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------- #
# The method loop (online view memory + Layer-3 verify) on Snowflake
# --------------------------------------------------------------------------- #
def _save(tag, rows, client, verify, graphs=None):
    out = os.path.join(RESULTS_DIR, f"{tag}_sf_method.json")
    json.dump({"verify": verify, "rows": rows, "n_ok": sum(r["correct"] for r in rows),
               "reuse": sum(r["reused"] for r in rows), "gen": sum(r["generated"] for r in rows),
               "sf_exec_seconds": client.exec_seconds, "sf_n_run": client.n_run,
               "llm_usage": USAGE.snapshot()}, open(out, "w"), indent=2)
    # dump the final per-DB view graphs (every CTE body + edges) for later inspection
    if graphs:
        from dataclasses import asdict
        gdump = {db: {"views": {n: asdict(v) for n, v in g.views.items()},
                      "n_views": g.n_views()} for db, g in graphs.items()}
        json.dump(gdump, open(os.path.join(RESULTS_DIR, f"{tag}_sf_graphs.json"), "w"), indent=2)
    return out


def _init_graph(db: str, seed_dir: str) -> Tuple[ViewGraph, set]:
    """Config S: load the frozen cold-start seed graph for this DB if present, else empty (config A).
    Returns (graph, seed_view_names) so reuse can be split seed-vs-online."""
    if seed_dir:
        sp = os.path.join(seed_dir, f"{db}.json")
        if os.path.exists(sp):
            g = sqlview.load_graph(sp)
            return g, set(g.views.keys())
    return ViewGraph(db_id=db), set()


def run(n, dbs, verify, sleep, max_views, model, tag, seed_dir=""):
    tasks = load_sf_tasks(n, dbs)
    client = SFClient()
    llm = LLM(model=model)
    emb = Embedder()
    graphs: Dict[str, ViewGraph] = {}
    seed_names: Dict[str, set] = {}
    rows = []
    cfg = "S(seed)" if seed_dir else ("A" if verify > 0 else "B")
    print(f"SF method run [{cfg}]: {len(tasks)} tasks | verify={verify} seed_dir={seed_dir or '-'}\n")
    for ti, t in enumerate(tasks):
        if ti and ti % 20 == 0:                          # periodic checkpoint
            _save(tag, rows, client, verify, graphs)
        db = t["db"]
        schema = render_sf_schema(db)
        ev = _evidence(t)
        # Memory scoping (mirrors realrun.py:324): config B (verify==0) RESETS the graph every
        # question (faithful AV-SQL, no cross-question memory); config A/S (verify>0) PERSIST the
        # graph across a DB's questions. Config S additionally LOADS a frozen cold-start seed graph
        # at each DB's first question, so reuse can fire from question 1 (no cold start).
        if verify <= 0:
            graphs[db] = ViewGraph(db_id=db)
        elif db not in graphs:
            graphs[db], seed_names[db] = _init_graph(db, seed_dir)
        g = graphs.setdefault(db, ViewGraph(db_id=db))
        _rw, rw = agents.rewrite_question(llm, schema, t["question"], ev)
        reqs, _raw, _sel = agents.propose_views(llm, schema, rw, max_views=max_views)

        chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
        reused_names = []                                # views reused this question (for Layer-4 learning)
        sn = seed_names.get(db, set())
        subgoals = []                                    # full per-sub-goal trace (decision + CTE)
        for req in reqs:
            # Reuse decision is made by the LLM over a candidate LIST (embedding is only a coarse
            # list-trimmer, never the final decider). Reject-biased: reuse only on a strict majority
            # of `verify` voters agreeing on the SAME view; any split / abstention => generate fresh.
            # verify == 0 is an explicit "never reuse" mode (config B: regenerate every sub-goal).
            spec = None
            # embedding-free shortlist: mechanical guard + lexical top-k (emb=None), then LLM decides
            cands = sqlview.retrieve_candidates(g, req, embedder=None, k=6) if verify > 0 else []
            votes = []
            if cands:
                picks = [agents.choose_reuse(llm, req, cands) for _ in range(verify)]
                votes = [{"choice": p[0], "reason": p[1], "confidence": p[2]} for p in picks]
                names = [p[0] for p in picks if p[0]]
                if names:
                    top, cnt = Counter(names).most_common(1)[0]
                    if cnt * 2 > verify:                          # strict majority of ALL voters
                        spec = next(c for c in cands if c.name == top)
                if spec is None:
                    vrej += 1                                     # candidates existed, LLM chose fresh
            if spec is not None:
                chosen.append(spec)
                reused += 1
                reused_names.append(spec.name)
                if spec.name in sn:
                    seed_reused += 1
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "REUSE", "view": spec.name, "from_seed": spec.name in sn,
                                 "candidates": [c.name for c in cands], "votes": votes,
                                 "cte": spec.body_sql})
                continue
            cand = gen_sf_view(llm, schema, req, list(g.views.values()))
            if cand is None:
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "GEN_FAILED", "candidates": [c.name for c in cands],
                                 "votes": votes})
                continue
            if g.has(cand.name):
                cand.name = f"{cand.name}_{len(g.views)}"
            g.add_view(cand)
            ok, vmsg = validate_sf_view(client, g, cand)          # FREE describe
            if ok:
                chosen.append(cand)
                gen += 1
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "GENERATE", "view": cand.name,
                                 "candidates": [c.name for c in cands], "votes": votes,
                                 "output_columns": cand.output_columns, "grain": cand.grain,
                                 "cte": cand.body_sql})
            else:
                g.remove_view(cand.name)
                subgoals.append({"subgoal": req.text, "category": req.category,
                                 "decision": "GEN_INVALID", "view": cand.name,
                                 "validate_error": vmsg, "candidates": [c.name for c in cands],
                                 "votes": votes, "cte": cand.body_sql})

        # compose final query
        composed = None
        plan = None
        if chosen:
            plan = agents.planner(llm, schema, rw, chosen)
            final = compose_sf_final(llm, schema, t["question"], ev, chosen, plan)
            if final:
                try:
                    composed = compose_sql(g, [v.name for v in chosen], final)
                except Exception:  # noqa: BLE001
                    composed = None
        if composed is None:
            composed = gen_sf_direct(llm, schema, t["question"], ev)

        # AV-SQL Stage 3 execution-repair loop: REVISE the composed view-SQL with error feedback
        # (agents.revise_sql role), NOT regenerate a fresh direct query — this preserves the view
        # structure across repair, exactly like realrun.py. Free `describe` compile-check first so
        # a compile error is caught without spending warehouse time.
        df, err = None, "no sql"
        for attempt in range(SQL_REPAIR_ATTEMPTS):
            if not composed:
                break
            ok, derr, _c = client.describe(composed)
            if not ok:
                err = derr[:200]
                if attempt < SQL_REPAIR_ATTEMPTS - 1:
                    composed = revise_sf_sql(llm, schema, t["question"], ev, composed, err) or composed
                continue
            try:
                df = client.run(composed, sleep_s=sleep)
                err = ""
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                df = None
                if attempt < SQL_REPAIR_ATTEMPTS - 1:
                    composed = revise_sf_sql(llm, schema, t["question"], ev, composed, err) or composed

        # AV-SQL Stage 3 semantic Revisor: verify the executing query truly answers the intent;
        # accept the revision only if it still executes (mirrors realrun.py).
        revised = False
        if df is not None and composed:
            preview = str(df.head(3).values.tolist())[:300]
            sem = semantic_revise_sf(llm, schema, rw, t["question"], ev, composed, preview)
            if sem and sem.strip() != composed.strip():
                try:
                    df2 = client.run(sem, sleep_s=sleep)
                    composed, df, revised = sem, df2, True
                except Exception:  # noqa: BLE001
                    pass                                  # keep the pre-revision query
        correct, serr = (score(df, t) if df is not None else (False, err))
        correct_b = bool(correct)
        # Layer 4: learn each reused view's boundary from this question's outcome — a correct reuse
        # is a validated_on example; a reuse that led to a wrong answer is a counter_example. Mirrors
        # realrun.py:346-354. The grown graph is persisted per DB below.
        for nm in reused_names:
            v = g.views.get(nm)
            if v is None:
                continue
            if correct_b and t["question"] not in v.validated_on:
                v.validated_on = (v.validated_on + [t["question"]])[-10:]
            elif (not correct_b) and t["question"] not in v.counter_examples:
                v.counter_examples = (v.counter_examples + [t["question"]])[-10:]
        rows.append({"instance_id": t["instance_id"], "db": db, "correct": correct_b,
                     "reused": reused, "seed_reused": seed_reused, "generated": gen,
                     "verify_reject": vrej, "sem_revised": revised, "graph_views": g.n_views(),
                     "seed_views": len(sn), "error": err or serr,
                     # full trace for later inspection of CTEs + model reasoning:
                     "question": t["question"], "rewrite": rw, "plan": plan,
                     "subgoals": subgoals, "chosen_views": [v.name for v in chosen],
                     "pred_sql": composed})
        print(f"  {t['instance_id']:10} {db[:18]:18} ok={int(correct_b)} reuse={reused}"
              f"(seed={seed_reused}) gen={gen} vrej={vrej} graph={g.n_views()} "
              f"exec={client.exec_seconds:6.1f}s {('' if correct_b else (err or serr)[:44])}", flush=True)

    n_ok = sum(r["correct"] for r in rows)
    tot_reuse = sum(r["reused"] for r in rows)
    tot_gen = sum(r["generated"] for r in rows)
    print(f"\n=== SF method summary (verify={verify}) ===")
    print(f"  tasks {len(rows)} | correct {n_ok} ({100*n_ok/max(1,len(rows)):.1f}%) | "
          f"reuse {tot_reuse} | gen {tot_gen} | verify_rejects {sum(r['verify_reject'] for r in rows)}")
    print(f"  Snowflake executed {client.n_run} queries | {client.exec_seconds:.1f}s warehouse-attached")
    out = _save(tag, rows, client, verify, graphs)
    print(f"  wrote {out}")
    client.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--dbs", default="")
    ap.add_argument("--verify", type=int, default=3,
                    help="number of LLM reuse-selector voters (reject-biased strict majority); "
                         "0 disables reuse entirely (config B: always generate fresh)")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="sfm")
    ap.add_argument("--seed_dir", default="",
                    help="config S: dir of frozen cold-start seed graphs ({db}.json). Requires verify>0.")
    args = ap.parse_args()
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    run(args.n, dbs, args.verify, args.sleep, args.max_views, args.model, args.tag,
        seed_dir=args.seed_dir)


if __name__ == "__main__":
    main()
