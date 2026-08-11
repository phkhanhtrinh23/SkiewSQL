"""Run the SkiewSQL config-A pipeline (schema-free rewrite + N×M decompose-and-align + ReFoRCE +
view-memory) on LiveSQLBench (birdsql/livesqlbench-base-full-v1), natively on PostgreSQL.

Databases are the BIRD-Interact Postgres dumps (loaded locally); the per-DB `schema.txt` gives the
DDL used for chunk-select; scoring is execution-match against the withheld `sol_sql` (now supplied via
the GT label file). Mirrors bq_method's structure (Postgres dialect here).
"""
from __future__ import annotations
import argparse, json, os, re, signal, glob
from typing import Dict, List, Optional, Tuple
import psycopg

from skiewsql import agents, sqlview, table_catalog, reforce_modules
from skiewsql.core import ViewGraph, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE

# --- config: where the loaded Postgres + downloaded schema.txt live -------------------------------
PG_HOST = os.environ.get("LIVESQL_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("LIVESQL_PG_PORT", "5455"))
PG_USER = os.environ.get("LIVESQL_PG_USER", "root")
BASE = os.environ.get("LIVESQL_BASE",
    "/tmp/claude-1000/-home-trinh-Dropbox-thesis-skill-driven-agentic-view/"
    "21e89d44-b68d-44a2-90c0-52cb4ad1adb3/scratchpad/livesqlbench")
SCHEMA_DIR = os.path.join(BASE, "hf_kg")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skiewsql", "results_real")
# Per-question wall-clock cap. Raise it for Together (3 RPM throttle makes a multi-call question
# legitimately take many minutes): e.g. SKIEW_PER_Q=1800.
PER_Q = int(os.environ.get("SKIEW_PER_Q", "300"))


class _QT(BaseException):
    pass


def _alarm(s, f):
    raise _QT(f"question exceeded {PER_Q}s")


class PGClient:
    """One psycopg connection per LiveSQLBench database."""
    def __init__(self):
        self._cons: Dict[str, psycopg.Connection] = {}

    def con(self, db: str):
        if db not in self._cons:
            self._cons[db] = psycopg.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, dbname=db,
                                             autocommit=True, connect_timeout=15)
        return self._cons[db]

    def run(self, db: str, sql: str, limit: Optional[int] = None) -> List[tuple]:
        with self.con(db).cursor() as cur:
            cur.execute("SET statement_timeout = 60000")   # 60s server-side guard
            cur.execute(sql)
            rows = cur.fetchmany(limit) if limit else cur.fetchall()
        return rows

    def dry(self, db: str, sql: str) -> Tuple[bool, str, List[str]]:
        """Validate a CTE/query cheaply: run it with LIMIT 0 to get columns without scanning."""
        try:
            with self.con(db).cursor() as cur:
                cur.execute("SET statement_timeout = 30000")
                cur.execute(f"SELECT * FROM ({sql}) _v LIMIT 0")
                cols = [d.name for d in cur.description] if cur.description else []
            return True, "", cols
        except Exception as e:  # noqa: BLE001
            try: self.con(db).rollback()
            except Exception: pass
            return False, str(e)[:200], []


def pg_table_blocks(db: str) -> Dict[str, str]:
    """{table: CREATE TABLE DDL} parsed from the per-DB schema.txt."""
    p = os.path.join(SCHEMA_DIR, db, f"{db}_schema.txt")
    if not os.path.exists(p):
        return {}
    txt = open(p, encoding="utf-8", errors="ignore").read()
    # keep only the DDL parts; drop the "First 3 rows:" data previews
    blocks: Dict[str, str] = {}
    for m in re.finditer(r'CREATE TABLE\s+"?(\w+)"?\s*\((.*?)\n\)\s*;', txt, re.DOTALL):
        name = m.group(1)
        blocks[name] = f'CREATE TABLE "{name}" (\n{m.group(2).strip()}\n);'
    return blocks


def _score(client: PGClient, db: str, pred: Optional[str], sol_sqls: List[str]) -> Tuple[bool, str]:
    """Execution match: pred result-set equals gold result-set (order-insensitive)."""
    if not pred or not sol_sqls:
        return False, "no pred/gold"
    def rset(sql):
        rows = client.run(db, sql)
        return {tuple(str(x) for x in r) for r in rows}, len(rows)
    try:
        pset, _pn = rset(pred)
    except Exception as e:  # noqa: BLE001
        return False, f"pred exec: {str(e)[:120]}"
    for gold in sol_sqls:                                   # any gold variant matching counts
        try:
            gset, _gn = rset(gold)
        except Exception:
            continue
        if pset == gset:
            return True, ""
    return False, "result mismatch"


def gen_pg_view(llm, schema, req, existing, reforce="") -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = ("You MAY build on these existing views (SELECT FROM them, list in depends_on):\n"
              + "\n".join(f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]) + "\n")
    sys = ("You build ONE reusable PostgreSQL CTE body: a single SELECT (no WITH, no trailing ;). "
           "Double-quote identifiers as in the DDL; JSONB columns use ->/->>/jsonb operators. Carry "
           "key/id columns so the view stays joinable. Lift question-specific literals OUT. Output one "
           "```sql block then one ```json metadata block.")
    user = (f"PostgreSQL schema (DDL):\n{schema}\n\nBuild view `{req.want_name}` (category {req.category}). "
            f"Meaning: {req.text}\nRequired outputs (alias EXACTLY): {req.required_outputs}\n"
            f"Grain (one row per): {req.required_grain}\n{ex}{reforce}\n"
            '```sql\nSELECT ...\n```\n```json\n{"output_columns": [], "source_tables": [], "grain": [], "depends_on": []}\n```')
    txt = llm.ask(sys, user, tag="lsql_view", max_tokens=1400)
    body = extract_code(txt, langs=("sql", "cte")); meta = extract_json(txt) or {}
    if not body:
        return None
    outs = [str(x) for x in (meta.get("output_columns") or req.required_outputs)]
    for r in req.required_outputs:
        if r.lower() not in {o.lower() for o in outs}: outs.append(r)
    deps = [str(d) for d in (meta.get("depends_on") or []) if any(d == v.name for v in existing)]
    return ViewSpec(name=req.want_name, category=req.category, body_sql=body.strip().rstrip(";"),
                    source_tables=[str(x) for x in (meta.get("source_tables") or [])], output_columns=outs,
                    grain=[str(x) for x in (meta.get("grain") or req.required_grain)],
                    semantic_filters={}, depends_on=deps, description=req.text)


def compose_pg_final(llm, schema, question, evidence, chosen, plan) -> Optional[str]:
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}" for v in chosen)
    txt = llm.ask("You are a PostgreSQL generator. The listed views are ALREADY defined as CTEs (do not "
                  "redefine). Write ONLY the final SELECT answering the question using them (and base "
                  "tables if needed). Apply question-specific filters/order/limit. Output one ```sql block.",
                  f"Schema:\n{schema}\n\nCTE views:\n{vs}\n\nQuestion: {question}\n{evidence}\nPlan:\n{plan}\n```sql\nSELECT ...\n```",
                  tag="lsql_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",)); return sql.strip().rstrip(";") if sql else None


def gen_pg_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask("You are a PostgreSQL generator. Output one ```sql block with a single executable "
                  "PostgreSQL query. Double-quote identifiers; JSONB via ->/->>. No explanation.",
                  f"Schema (DDL):\n{schema}\n\nQuestion: {question}\n{evidence}{err}\n```sql\nSELECT ...\n```",
                  tag="lsql_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",)); return sql.strip().rstrip(";") if sql else None


def validate_pg_view(client: PGClient, db: str, graph: ViewGraph, spec: ViewSpec) -> Tuple[bool, str]:
    try:
        deps = graph.topo_closure(spec.depends_on) if spec.depends_on else []
        chosen = {s.name: s for s in deps}; chosen[spec.name] = spec
        ordered = sqlview._order_specs(list(chosen.values()))
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {',\n'.join(s.cte_clause() for s in ordered)}\nSELECT * FROM {spec.name}"
        ok, err, cols = client.dry(db, sql)
        if not ok: return False, err
        missing = [c for c in spec.output_columns if c.lower() not in {x.lower() for x in cols}]
        return (not missing), ("ok" if not missing else f"missing {missing}")
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:150]


def _pack(blocks: Dict[str, str], budget=12000) -> List[str]:
    chunks, cur, n = [], [], 0
    for b in blocks.values():
        if n + len(b) > budget and cur: chunks.append("\n\n".join(cur)); cur, n = [], 0
        cur.append(b); n += len(b)
    if cur: chunks.append("\n\n".join(cur))
    return chunks or [""]


def run(n, dbs, verify, model, tag, nxm=True, max_subgoals=4, use_reforce=True):
    tasks = json.load(open(os.path.join(BASE, "tasks.json")))
    if dbs: tasks = [t for t in tasks if t["db"] in dbs]
    tasks = tasks[:n]
    client = PGClient(); llm = LLM(model=model); emb = Embedder()
    graphs: Dict[str, ViewGraph] = {}
    rows = []
    print(f"LiveSQLBench run [A]: {len(tasks)} tasks | verify={verify} nxm={nxm}\n", flush=True)
    signal.signal(signal.SIGALRM, _alarm)
    for ti, t in enumerate(tasks):
        signal.alarm(PER_Q)
        try:
            db = t["db"]; ev = f"External knowledge:\n{t['evidence']}" if t.get("evidence") else ""
            blocks = pg_table_blocks(db)
            schema = table_catalog.render_selected(blocks, list(blocks), budget=24000) if blocks else ""
            if verify <= 0: graphs[db] = ViewGraph(db_id=db)
            g = graphs.setdefault(db, ViewGraph(db_id=db))
            _rw, rw = agents.rewrite_question(llm, "", t["question"], ev)
            per_tables = {}
            if nxm:
                reqs, per_tables, _ = agents.decompose_and_align(llm, _pack(blocks), rw,
                    ", ".join(blocks.keys()), max_subgoals=max_subgoals, qualify_outputs=False, tag_prefix="ls_")
            else:
                reqs, _r, _s = agents.propose_views(llm, schema, rw, max_views=3)
            reforce = ""
            if use_reforce:
                fmt = reforce_modules.format_answer(llm, t["question"])
                if fmt: reforce = "\nREQUIRED ANSWER FORMAT:\n" + fmt + "\n"
            chosen, reused, gen = [], 0, 0
            for req in reqs:
                spec = None
                if verify > 0:
                    if sqlview.deterministic_reuse_on():
                        spec, _d = sqlview.select_reuse(g, req, emb, tau=0.55)
                    else:
                        spec, _d = sqlview.retrieve(g, req, emb, tau=0.55)
                        if spec is not None and sum(int(agents.verify_reuse(llm, spec, req)[0]) for _ in range(verify)) * 2 < verify:
                            spec = None
                if spec is not None:
                    chosen.append(spec); reused += 1; continue
                req_schema = (table_catalog.render_selected(blocks, list(per_tables[req.want_name]), budget=24000)
                              if per_tables.get(req.want_name) else schema)
                cand = gen_pg_view(llm, req_schema, req, list(g.views.values()), reforce=reforce)
                if cand is None: continue
                if g.has(cand.name): cand.name = f"{cand.name}_{len(g.views)}"
                g.add_view(cand)
                ok, _m = validate_pg_view(client, db, g, cand)
                if ok: chosen.append(cand); gen += 1
                else: g.remove_view(cand.name)
            composed = None
            if chosen:
                plan = agents.planner(llm, schema, rw, chosen)
                final = compose_pg_final(llm, schema, t["question"], ev, chosen, plan)
                if final:
                    try: composed = compose_sql(g, [v.name for v in chosen], final)
                    except Exception: composed = None
            if composed is None:
                composed = gen_pg_direct(llm, schema, t["question"], ev)
            # execute + small repair
            correct, serr = False, "no sql"
            for att in range(3):
                if not composed: break
                c2, e2 = _score(client, db, composed, t["sol_sql"])
                if c2: correct = True; serr = ""; break
                serr = e2
                if att < 2 and "exec" in e2:
                    composed = gen_pg_direct(llm, schema, t["question"], ev, prior_error=e2) or composed
                else: break
            rows.append({"instance_id": t["instance_id"], "db": db, "correct": bool(correct),
                         "reused": reused, "generated": gen, "pred_sql": composed, "error": serr})
            print(f"  {t['instance_id']:22} {db[:16]:16} ok={int(correct)} reuse={reused} gen={gen} "
                  f"[{sum(r['correct'] for r in rows)}/{len(rows)}] {('' if correct else serr[:34])}", flush=True)
        except (_QT, Exception) as e:  # noqa: BLE001
            rows.append({"instance_id": t["instance_id"], "db": t.get("db"), "correct": False,
                         "reused": 0, "generated": 0, "pred_sql": None, "error": f"{type(e).__name__}: {str(e)[:80]}"})
            print(f"  {t['instance_id']:22} ERR {str(e)[:40]}", flush=True)
        finally:
            signal.alarm(0)
        if ti % 20 == 0:
            json.dump(rows, open(os.path.join(RESULTS_DIR, f"{tag}_livesql.json"), "w"), indent=1)
    nok = sum(r["correct"] for r in rows)
    json.dump(rows, open(os.path.join(RESULTS_DIR, f"{tag}_livesql.json"), "w"), indent=1)
    print(f"\n=== LiveSQLBench [A]: {nok}/{len(rows)} = {100*nok/max(1,len(rows)):.1f}% ===", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--dbs", default="")
    ap.add_argument("--verify", type=int, default=3)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="lsqlA")
    ap.add_argument("--nxm", type=int, default=1)
    ap.add_argument("--max_subgoals", type=int, default=4)
    ap.add_argument("--reforce", type=int, default=1)
    a = ap.parse_args()
    run(a.n, [d.strip() for d in a.dbs.split(",") if d.strip()] or None, a.verify, a.model, a.tag,
        nxm=bool(a.nxm), max_subgoals=a.max_subgoals, use_reforce=bool(a.reforce))


if __name__ == "__main__":
    main()
