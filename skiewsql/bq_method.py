"""bq_method.py — run the SkiewSQL view-memory method (retrieve-or-generate reusable CTEs) WITH the Layer 3 adversarial verifier, natively on BigQuery, staying inside the 1 TiB/month free tier. Cost discipline:
  * CTE validation uses BigQuery DRY-RUN only (scans 0 bytes = FREE): it confirms the CTE is valid BigQuery SQL and exposes the declared output columns, which is all `validate_view` needs.
  * Only the FINAL composed query per question is actually executed (cost-guarded + a sleep between executions to be gentle on quota / rate limits).

Reuses: core.ViewGraph / ViewSpec / ViewRequest / compose_sql, sqlview.retrieve, agents (rewrite, propose_views, planner, verify_reuse), and BQClient / render_bq_schema / load_bq_tasks / score from spider2bq. Generation of executable SQL (view bodies + final query) is BigQuery-dialect here."""
from __future__ import annotations

import argparse
import json
import os
import time
import signal
from typing import Dict, List, Optional, Tuple

from skiewsql import agents, sqlview, valuelink
from skiewsql.core import ViewGraph, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE
from skiewsql import table_catalog, reforce_modules
from skiewsql.paths import BIGQUERY_RUNS_DIR, ensure_dir
from skiewsql.spider2bq import (BQClient, render_bq_schema, bq_table_blocks, load_bq_tasks, score, _evidence,
                                PRICE_PER_TB)

RESULTS_DIR = ensure_dir(BIGQUERY_RUNS_DIR)

# Cost guard on ReFoRCE exploration probes (GB a single SELECT-DISTINCT probe may scan). Was referenced but never defined (NameError silently killed BQ exploration). Now defined and env-configurable. With unlimited BigQuery quota, set SKIEW_PROBE_MAX_GB high to let probes run.
PROBE_MAX_GB = float(os.environ.get("SKIEW_PROBE_MAX_GB", "2.0"))


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
{existing}{reforce}{error}
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


def gen_bq_view(llm, schema, req, existing, reforce="") -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = ("You MAY build on these existing views (SELECT FROM them, list in depends_on):\n"
              + "\n".join(f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]) + "\n")
    txt = llm.ask(VIEW_SYS, VIEW_USER.format(schema=schema, name=req.want_name,
                  category=req.category, desc=req.text, outs=req.required_outputs,
                  grain=req.required_grain, existing=ex, reforce=reforce, error=""), tag="bq_view", max_tokens=1400)
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
    txt = llm.ask(FINAL_SYS, FINAL_USER.format(schema=schema, views=vs, question=question,
                  evidence=evidence, plan=plan), tag="bq_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def gen_bq_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema, question=question,
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


def _pack_blocks(blocks: Dict[str, str], budget: int = 12000) -> List[str]:
    """Char-pack whole table DDL blocks into <=budget chunks (N×M alignment chunks for BigQuery)."""
    chunks, cur, cur_len = [], [], 0
    for _t, blk in blocks.items():
        if cur_len + len(blk) > budget and cur:
            chunks.append("\n\n".join(cur)); cur, cur_len = [], 0
        cur.append(blk); cur_len += len(blk) + 2
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks or [""]


PER_Q_BQ = int(os.environ.get("SKIEW_PER_Q", "300"))  # per-question wall-clock cap (SIGALRM). Bounds slow/stalled ga360-class questions. Raise via SKIEW_PER_Q for slow providers (Together A ~11min/q)


class _BQTimeout(BaseException):
    # BaseException so it unwinds past every inner `except Exception` (same fix as realrun._QTimeout).
    pass


def _bq_alarm(signum, frame):
    raise _BQTimeout(f"question exceeded {PER_Q_BQ}s")


def run(n, dbs, verify, sleep, max_gb, max_views, model, tag, budget_tib=0.5, seed_dir="",
        use_reforce=False, nxm=False, max_subgoals=8, architecture="legacy",
        focused_budget=6000):
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
    signal.signal(signal.SIGALRM, _bq_alarm)
    for ti, t in enumerate(tasks):
        if client.bytes_billed / 1e12 > budget_tib:      # cumulative free-tier safety cap
            print(f"  STOP: cumulative {client.bytes_billed/1e12:.3f} TiB > budget {budget_tib} TiB")
            break
        if ti and ti % 20 == 0:                          # periodic checkpoint
            _save(tag, rows, client, verify, graphs)
        signal.alarm(PER_Q_BQ)
        try:
            db = t["db"]
            # DESCRIPTION-CATALOG SCHEMA SELECTION (replaces the `[:16000]` prefix slice). Spider 2.0 BigQuery schemas reach 836k chars. A prefix showed <2% of the database. We build a one-line description per table ONCE per db (cached), shortlist the tables this question needs from that catalog, and render those tables IN FULL.
            blocks = bq_table_blocks(db)
            catalog = table_catalog.build_catalog(llm, db, blocks)
            picked = table_catalog.shortlist(llm, t["question"], catalog, k=8, evidence=_evidence(t))
            schema = table_catalog.render_selected(blocks, picked, budget=24000)

            _BQ_VP_MAX_GB = float(os.environ.get("SKIEW_BQ_VP_MAX_GB", "1.0"))
            def _bq_vp(db=db, tables=list(picked)):   # value profile (BigQuery): gb-guarded per table
                def samp(tb):
                    q = f"SELECT * FROM `{db}.{tb}` LIMIT 500"
                    try:
                        ok, _err, _c, gb = client.dry(q)
                        if not ok or gb > _BQ_VP_MAX_GB:      # skip tables that would scan too much $
                            return [], []
                        d = client.run(q, cap_rows=500)
                        return list(d.columns), d.values.tolist()
                    except Exception:  # noqa: BLE001
                        return [], []
                return samp, tables
            schema += valuelink.value_profile_appendix(f"bq:{db}", _bq_vp)

            # ReFoRCE format restriction (question-level). Column exploration is per sub-goal below, so the evidence reaches gen_bq_view — the step that actually chooses columns.
            reforce = ""
            if use_reforce:
                fmt = reforce_modules.format_answer(llm, t["question"])
                if fmt:
                    reforce += ("\nREQUIRED ANSWER FORMAT (return EXACTLY these columns, in this order, "
                                "nothing more):\n" + fmt + "\n")
            ev = _evidence(t)
            # Memory scoping: config B (verify==0) RESETS the graph per question (faithful AV-SQL, no cross-question memory). Config A/S (verify>0) PERSIST. Config S also LOADS a seed graph.
            if verify <= 0:
                graphs[db] = ViewGraph(db_id=db)
            elif db not in graphs:
                graphs[db], seed_names[db] = _init_graph(db, seed_dir)
            g = graphs.setdefault(db, ViewGraph(db_id=db))
            sn = seed_names.get(db, set())
            _rw, rw = agents.rewrite_question(llm, "", t["question"], ev)  # schema-free rewrite
            per_tables: Dict[str, set] = {}
            architecture_route = ("nxm" if nxm else architecture)
            direct_route, adaptive_selected = False, set()
            packed = _pack_blocks(blocks)
            packed_with_tables = [
                (chunk, [name for name, block in blocks.items() if block in chunk])
                for chunk in packed]
            if architecture == "auto":
                reqs, per_tables, adaptive_route, adaptive_selected, _ncalls = agents.adaptive_requests(
                    llm, packed_with_tables, rw, ", ".join(blocks.keys()),
                    render_selected=lambda tabs: table_catalog.render_selected(
                        blocks, list(tabs), budget=10**9),
                    estimate_tokens=lambda text: max(1, len(text) // 4),
                    focused_budget=focused_budget, max_subgoals=max_subgoals,
                    qualify_outputs=False, tag_prefix="bq_")
                direct_route = adaptive_route == "direct_sql"
                architecture_route = (adaptive_route if direct_route else
                                      f"{adaptive_route}_{'graph' if verify > 0 else 'nograph'}")
            elif nxm or architecture == "nxm":
                # N×M: decompose once (whole-DB table index), align each of M sub-goals against all N DDL chunks. No cap at max_views.
                table_index = ", ".join(blocks.keys())
                # NOTE: qualify_outputs MUST be False on BigQuery. Qualified outputs alias columns as `table.column`, but BigQuery forbids dots in field names (backticked or not), so every such view fails the dry-run validation → gen=0. MariaDB (BEAVER) accepts dotted aliases. BigQuery does not, so we use bare outputs here (same regime as Spider2-lite, which works).
                reqs, per_tables, _ncalls = agents.decompose_and_align(
                    llm, packed, rw, table_index, max_subgoals=max_subgoals,
                    qualify_outputs=False, tag_prefix="bq_")
            else:
                reqs, _raw, _sel = agents.propose_views(llm, schema, rw, max_views=max_views)

            chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
            reused_names = []                                # views reused this question (Layer-4 learning)
            resolved_reqs = {}
            for req in reqs:
                spec = None
                if verify > 0:                                        # only config A/S reuse
                    if sqlview.deterministic_reuse_on():              # Zero-Mem: guard+embedding, no LLM
                        spec, _d = sqlview.select_reuse(g, req, emb, tau=0.55)
                    else:
                        spec, _d = sqlview.retrieve(g, req, emb, tau=0.55)
                        if spec is not None:                          # Layer 3 gate (LLM verify)
                            allows = sum(int(agents.verify_reuse(llm, spec, req)[0]) for _ in range(verify))
                            if allows * 2 < verify:
                                spec, vrej = None, vrej + 1
                if spec is not None:
                    if spec.name in sn:
                        seed_reused += 1
                    chosen.append(spec)
                    reused += 1
                    reused_names.append(spec.name)
                    resolved_reqs[req.want_name] = spec
                    continue
                # N×M: each sub-goal generates against ONLY its aligned tables. Else the shortlisted schema.
                req_schema = (table_catalog.render_selected(blocks, list(per_tables[req.want_name]),
                                                            budget=24000)
                              if per_tables.get(req.want_name) else schema)
                sub_rf = reforce
                if use_reforce:
                    def _probe(q, _c=client):
                        ok, err, _cols, gb = _c.dry(q)          # FREE dry-run first
                        if not ok:
                            raise RuntimeError(err)
                        if gb > PROBE_MAX_GB:                    # cost guard on exploration probes
                            raise RuntimeError(f"probe would scan {gb:.2f} GB > {PROBE_MAX_GB} GB")
                        return _c.run(q, cap_rows=5).to_string(index=False)
                    pre_info, _n = reforce_modules.exploration(
                        llm, _probe,
                        f"{req.text} (required outputs: {req.required_outputs}. Grain: {req.required_grain})",
                        req_schema[:6000], api="bigquery")
                    if pre_info:
                        sub_rf += ("\nColumn exploration — VALUES observed for this sub-goal:\n"
                                   + pre_info[:4000] + "\n")
                declared = [resolved_reqs[n] for n in req.depends_on if n in resolved_reqs]
                missing_deps = [n for n in req.depends_on if n not in resolved_reqs]
                if missing_deps and not req.may_read_base_tables:
                    continue
                offered = declared if req.depends_on else list(g.views.values())
                cand = (agents.av_view(llm, req_schema, rw, req.want_name, evidence=ev,
                                       dialect="BigQuery")
                        if req.holistic else
                        gen_bq_view(llm, req_schema, req, offered, reforce=sub_rf))
                if cand is None:
                    continue
                if req.depends_on and not req.may_read_base_tables:
                    cand.depends_on = list(dict.fromkeys(cand.depends_on + [v.name for v in declared]))
                if g.has(cand.name):
                    cand.name = f"{cand.name}_{len(g.views)}"
                g.add_view(cand)
                ok, _msg = validate_bq_view(client, g, cand)          # FREE dry-run
                if ok:
                    chosen.append(cand)
                    gen += 1
                    resolved_reqs[req.want_name] = cand
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
                direct_schema = (table_catalog.render_selected(
                    blocks, list(adaptive_selected), budget=24000)
                    if direct_route and adaptive_selected else schema)
                composed = gen_bq_direct(llm, direct_schema, t["question"], ev)

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
            # Layer 4: learn each reused view's boundary (correct reuse -> validated_on. Wrong -> counter _example). Mirrors realrun.py:346-354. Grown graph persisted via _save's asdict dump.
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
                         "pred_sql": composed, "error": err or serr,
                         "architecture_route": architecture_route})
            print(f"  {t['instance_id']:8} {db:14} ok={int(correct)} reuse={reused}(seed={seed_reused}) "
                  f"gen={gen} vrej={vrej} route={architecture_route} graph={g.n_views()} cost=${client.cost_usd:.4f} "
                  f"{('' if correct else (err or serr)[:44])}", flush=True)
        except (_BQTimeout, Exception) as _e:  # noqa: BLE001 - one slow/bad question must not stall the run
            rows.append({"instance_id": t["instance_id"], "db": t["db"], "correct": False,
                         "reused": 0, "seed_reused": 0, "generated": 0, "verify_reject": 0,
                         "graph_views": 0, "seed_views": 0, "pred_sql": None,
                         "error": f"{type(_e).__name__}: {str(_e)[:120]}",
                         "architecture_route": "failed"})
            print(f"  {t['instance_id']:8} {t['db']:14} TIMEOUT/ERR {str(_e)[:44]}", flush=True)
        finally:
            signal.alarm(0)

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
    ap.add_argument("--architecture", default="legacy", choices=["legacy", "auto", "nxm"])
    ap.add_argument("--focused_budget", type=int, default=6000,
                    help="deprecated compatibility knob. Auto now routes by semantic difficulty")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="bqm")
    ap.add_argument("--reforce", type=int, default=0,
                    help="1 = ReFoRCE format restriction + per-sub-goal column exploration (probes are dry-run cost-gated)")
    ap.add_argument("--nxm", type=int, default=0,
                    help="1 = N×M decomposition: decompose once (whole-DB table index), align each of "
                         "M sub-goals against all N DDL chunks (no cap at max_views)")
    ap.add_argument("--max_subgoals", type=int, default=4, help="N×M mode: cap on M sub-goals")
    ap.add_argument("--budget_tib", type=float, default=0.5, help="cumulative scan cap (TiB)")
    ap.add_argument("--seed_dir", default="", help="config S: dir of frozen seed graphs ({db}.json)")
    args = ap.parse_args()
    if args.nxm:
        args.architecture = "nxm"
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    run(args.n, dbs, args.verify, args.sleep, args.max_gb, args.max_views, args.model, args.tag,
        budget_tib=args.budget_tib, seed_dir=args.seed_dir, use_reforce=bool(args.reforce),
        nxm=bool(args.nxm), max_subgoals=args.max_subgoals,
        architecture=args.architecture, focused_budget=args.focused_budget)


if __name__ == "__main__":
    main()
