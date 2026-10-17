"""Run the SkiewSQL config-A pipeline (schema-free rewrite + N×M decompose-and-align + ReFoRCE + view-memory) on LiveSQLBench (birdsql/livesqlbench-base-full-v1), natively on PostgreSQL. Databases are the BIRD-Interact Postgres dumps (loaded locally). The per-DB `schema.txt` gives the DDL used for chunk-select. Scoring is execution-match against the withheld `sol_sql` (now supplied via the GT label file). Mirrors bq_method's structure (Postgres dialect here)."""
from __future__ import annotations
import argparse, json, os, re, signal, glob
from typing import Dict, List, Optional, Tuple
import psycopg

from skiewsql import agents, sqlview, table_catalog, reforce_modules, valuelink
from skiewsql.core import SkillRegistry, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE
from skiewsql.paths import LIVESQL_RUNS_DIR, ensure_dir
from skiewsql.prompt_loader import load_prompt

EXISTING_VIEWS = load_prompt("shared/existing_views.txt")

# --- config: where the loaded Postgres + downloaded schema.txt live -------------------------------
PG_HOST = os.environ.get("LIVESQL_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("LIVESQL_PG_PORT", "5455"))
PG_USER = os.environ.get("LIVESQL_PG_USER", "root")
BASE = os.environ.get("LIVESQL_BASE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "livesqlbench"))  # Holds tasks.json + hf_kg/
SCHEMA_DIR = os.path.join(BASE, "hf_kg")
RESULTS_DIR = ensure_dir(LIVESQL_RUNS_DIR)
# Per-question wall-clock cap. Raise it for Together (3 RPM throttle makes a multi-call question legitimately take many minutes): e.g. SKIEW_PER_Q=1800.
PER_Q = int(os.environ.get("SKIEW_PER_Q", "300"))

VIEW_SYS = load_prompt("livesql_method/view_sys.txt")
VIEW_USER = load_prompt("livesql_method/view_user.txt")
FINAL_SYS = load_prompt("livesql_method/final_sys.txt")
FINAL_USER = load_prompt("livesql_method/final_user.txt")
DIRECT_SYS = load_prompt("livesql_method/direct_sys.txt")
DIRECT_USER = load_prompt("livesql_method/direct_user.txt")


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
    # Some full-v1 schema.txt files quote bare SQL keywords ("CREATE" TABLE, "PRIMARY" KEY, "FOREIGN" KEY) — a curation quirk. Tolerate the optional quotes when matching and strip them from the emitted DDL so the model sees clean SQL. keep only the DDL parts. Drop the "First 3 rows:" data previews
    blocks: Dict[str, str] = {}
    for m in re.finditer(r'"?CREATE"?\s+TABLE\s+"?(\w+)"?\s*\((.*?)\n\)\s*;', txt, re.DOTALL):
        name = m.group(1)
        body = m.group(2).strip()
        for kw in ("PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "REFERENCES", "KEY"):
            body = re.sub(rf'"{kw}"', kw, body)
        blocks[name] = f'CREATE TABLE "{name}" (\n{body}\n);'
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
        ex = EXISTING_VIEWS.format(views="\n".join(
            f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]))
    user = VIEW_USER.format(schema=schema, name=req.want_name, category=req.category,
                            meaning=req.text, outputs=req.required_outputs,
                            grain=req.required_grain, existing=ex, reforce=reforce)
    txt = llm.ask(VIEW_SYS, user, tag="lsql_view", max_tokens=1400)
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
    user = FINAL_USER.format(schema=schema, views=vs, question=question,
                             evidence=evidence, plan=plan)
    txt = llm.ask(FINAL_SYS, user, tag="lsql_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",)); return sql.strip().rstrip(";") if sql else None


def gen_pg_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    user = DIRECT_USER.format(schema=schema, question=question, evidence=evidence, error=err)
    txt = llm.ask(DIRECT_SYS, user, tag="lsql_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",)); return sql.strip().rstrip(";") if sql else None


def validate_pg_view(client: PGClient, db: str, registry: SkillRegistry, spec: ViewSpec) -> Tuple[bool, str]:
    try:
        deps = registry.topo_closure(spec.depends_on) if spec.depends_on else []
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


def run(n, dbs, verify, model, tag, nxm=True, max_subgoals=4, use_reforce=True,
        architecture="legacy", focused_budget=6000):
    tasks = json.load(open(os.path.join(BASE, "tasks.json")))
    if dbs: tasks = [t for t in tasks if t["db"] in dbs]
    tasks = tasks[:n]
    client = PGClient(); llm = LLM(model=model); emb = Embedder()
    registries: Dict[str, SkillRegistry] = {}
    rows = []
    print(f"LiveSQLBench run [A]: {len(tasks)} tasks | verify={verify} nxm={nxm}\n", flush=True)
    signal.signal(signal.SIGALRM, _alarm)
    for ti, t in enumerate(tasks):
        signal.alarm(PER_Q)
        try:
            db = t["db"]; ev = f"External knowledge:\n{t['evidence']}" if t.get("evidence") else ""
            blocks = pg_table_blocks(db)
            schema = table_catalog.render_selected(blocks, list(blocks), budget=24000) if blocks else ""

            def _pg_vp(db=db, blocks=blocks):   # value profile (Postgres): sample each table once per db
                def samp(t):
                    try:
                        with client.con(db).cursor() as cur:
                            cur.execute(f'SELECT * FROM "{t}" LIMIT 500')
                            rws = cur.fetchall(); cols = [d[0] for d in cur.description]
                        return cols, rws
                    except Exception:  # noqa: BLE001
                        try: client.con(db).rollback()
                        except Exception: pass
                        return [], []
                return samp, list(blocks)
            schema += valuelink.value_profile_appendix(f"livesql:{db}", _pg_vp)
            if verify <= 0: registries[db] = SkillRegistry(db_id=db)
            g = registries.setdefault(db, SkillRegistry(db_id=db))
            _rw, rw = agents.rewrite_question(llm, "", t["question"], ev)
            per_tables = {}
            architecture_route = ("nxm" if nxm else architecture)
            direct_route, adaptive_selected = False, set()
            packed = _pack(blocks)
            packed_with_tables = [
                (chunk, [name for name, block in blocks.items() if block in chunk])
                for chunk in packed]
            if architecture == "auto":
                reqs, per_tables, adaptive_route, adaptive_selected, _ = agents.adaptive_requests(
                    llm, packed_with_tables, rw, ", ".join(blocks.keys()),
                    render_selected=lambda tabs: table_catalog.render_selected(
                        blocks, list(tabs), budget=10**9),
                    estimate_tokens=lambda text: max(1, len(text) // 4),
                    focused_budget=focused_budget, max_subgoals=max_subgoals,
                    qualify_outputs=False, tag_prefix="ls_")
                direct_route = adaptive_route == "direct_sql"
                architecture_route = (adaptive_route if direct_route else
                                      f"{adaptive_route}_{'registry' if verify > 0 else 'nomemory'}")
            elif nxm or architecture == "nxm":
                reqs, per_tables, _ = agents.decompose_and_align(llm, packed, rw,
                    ", ".join(blocks.keys()), max_subgoals=max_subgoals, qualify_outputs=False, tag_prefix="ls_")
            else:
                reqs, _r, _s = agents.propose_views(llm, schema, rw, max_views=3)
            reforce = ""
            if use_reforce:
                fmt = reforce_modules.format_answer(llm, t["question"])
                if fmt: reforce = "\nREQUIRED ANSWER FORMAT:\n" + fmt + "\n"
            chosen, reused, gen = [], 0, 0
            resolved_reqs = {}
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
                    chosen.append(spec); reused += 1; resolved_reqs[req.want_name] = spec; continue
                req_schema = (table_catalog.render_selected(blocks, list(per_tables[req.want_name]), budget=24000)
                              if per_tables.get(req.want_name) else schema)
                declared = [resolved_reqs[n] for n in req.depends_on if n in resolved_reqs]
                missing_deps = [n for n in req.depends_on if n not in resolved_reqs]
                if missing_deps and not req.may_read_base_tables:
                    continue
                offered = declared if req.depends_on else list(g.views.values())
                cand = (agents.av_view(llm, req_schema, rw, req.want_name, evidence=ev,
                                       dialect="PostgreSQL")
                        if req.holistic else
                        gen_pg_view(llm, req_schema, req, offered, reforce=reforce))
                if cand is None: continue
                if req.depends_on and not req.may_read_base_tables:
                    cand.depends_on = list(dict.fromkeys(cand.depends_on + [v.name for v in declared]))
                if g.has(cand.name): cand.name = f"{cand.name}_{len(g.views)}"
                g.add_view(cand)
                ok, _m = validate_pg_view(client, db, g, cand)
                if ok:
                    chosen.append(cand); gen += 1; resolved_reqs[req.want_name] = cand
                else: g.remove_view(cand.name)
            composed = None
            if chosen:
                plan = agents.planner(llm, schema, rw, chosen)
                final = compose_pg_final(llm, schema, t["question"], ev, chosen, plan)
                if final:
                    try: composed = compose_sql(g, [v.name for v in chosen], final)
                    except Exception: composed = None
            if composed is None:
                direct_schema = (table_catalog.render_selected(
                    blocks, list(adaptive_selected), budget=24000)
                    if direct_route and adaptive_selected else schema)
                composed = gen_pg_direct(llm, direct_schema, t["question"], ev)
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
                         "reused": reused, "generated": gen, "pred_sql": composed, "error": serr,
                         "architecture_route": architecture_route})
            print(f"  {t['instance_id']:22} {db[:16]:16} ok={int(correct)} reuse={reused} gen={gen} "
                  f"route={architecture_route} [{sum(r['correct'] for r in rows)}/{len(rows)}] "
                  f"{('' if correct else serr[:34])}", flush=True)
        except (_QT, Exception) as e:  # noqa: BLE001
            rows.append({"instance_id": t["instance_id"], "db": t.get("db"), "correct": False,
                         "reused": 0, "generated": 0, "pred_sql": None,
                         "error": f"{type(e).__name__}: {str(e)[:80]}",
                         "architecture_route": "failed"})
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
    ap.add_argument("--architecture", default="legacy", choices=["legacy", "auto", "nxm"])
    ap.add_argument("--focused_budget", type=int, default=6000,
                    help="deprecated compatibility knob. Auto now routes by semantic difficulty")
    ap.add_argument("--nxm", type=int, default=1)
    ap.add_argument("--max_subgoals", type=int, default=4)
    ap.add_argument("--reforce", type=int, default=1)
    a = ap.parse_args()
    if a.nxm and a.architecture == "legacy":
        a.architecture = "nxm"
    run(a.n, [d.strip() for d in a.dbs.split(",") if d.strip()] or None, a.verify, a.model, a.tag,
        nxm=bool(a.nxm), max_subgoals=a.max_subgoals, use_reforce=bool(a.reforce),
        architecture=a.architecture, focused_budget=a.focused_budget)


if __name__ == "__main__":
    main()
