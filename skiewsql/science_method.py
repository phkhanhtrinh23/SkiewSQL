"""science_method.py — run SkiewSQL (A/B/S) on the ScienceBenchmark benchmark, natively on PostgreSQL. ScienceBenchmark (Kosten et al.) ships 3 real-science databases as Postgres dumps — CORDIS (EU research), OncoMX (cancer genomics), SDSS (astrophysics) — with Spider-style gold SQL. We load them into a userspace Postgres 18 cluster (port 5433) and run BOTH the generated query and the gold on that same engine (Execution Match). Only the public `dev` split has gold, so we evaluate on it.

Direct Postgres port of beaver_method.py (same A/B/S control flow, reuse/verify/seed logic, honest non-trivial negative-reuse flag). Dialect for generation is PostgreSQL. Each DB's tables live in a named schema, set via search_path so gold + generated unqualified table refs resolve."""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter
from typing import Dict, List, Optional, Tuple

import pandas as pd
import psycopg

from skiewsql import agents, sqlview
from skiewsql.core import SkillRegistry, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE
from skiewsql.paths import SCIENCE_RUNS_DIR, ensure_dir

RESULTS_DIR = ensure_dir(SCIENCE_RUNS_DIR)
SCIENCE_ROOT = os.environ.get("SCIENCE_ROOT", os.path.join(_ROOT, "data", "sciencebenchmark"))

PG_HOST = os.environ.get("SCIENCE_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("SCIENCE_PG_PORT", "5433"))
PG_USER = os.environ.get("SCIENCE_PG_USER", os.environ.get("USER", "postgres"))

# benchmark dir -> (postgres dbname, schema the tables live in)
SCIENCE_DBS = {
    "cordis": {"dbname": "cordis", "schema": "unics_cordis"},
    "oncomx": {"dbname": "oncomx", "schema": "oncomx_v1_0_25"},
    "sdss": {"dbname": "sdss", "schema": "lite"},
}

SQL_REPAIR_ATTEMPTS = 5

PG_RULES = (
    "Use PostgreSQL dialect. A single schema is on the search_path, so do NOT schema-qualify tables — "
    "reference them by bare name as in the DDL. Identifiers are case-folded to lower-case unless "
    "double-quoted, so match the case shown in the schema. Use standard SQL / Postgres functions. "
    "Carry key/id columns through CTEs so views stay joinable. Single-quote string literals."
)


# --------------------------------------------------------------------------- #
# Postgres client (one connection per benchmark DB, search_path pinned)
# --------------------------------------------------------------------------- #
class PGClient:
    def __init__(self):
        self.conns: Dict[str, psycopg.Connection] = {}
        self.exec_seconds = 0.0
        self.n_run = 0

    def _conn(self, db: str) -> psycopg.Connection:
        info = SCIENCE_DBS[db]
        if db not in self.conns:
            c = psycopg.connect(host=PG_HOST, port=PG_PORT, dbname=info["dbname"], user=PG_USER,
                                autocommit=True, connect_timeout=15)
            with c.cursor() as cur:
                cur.execute(f'SET search_path TO {info["schema"]}, public')
                cur.execute("SET statement_timeout = 60000")     # 60s guard against runaway
            self.conns[db] = c
        return self.conns[db]

    def run(self, sql: str, db: str) -> pd.DataFrame:
        import time
        conn = self._conn(db)
        t0 = time.time()
        with conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
            cols = [d.name for d in c.description] if c.description else []
        self.exec_seconds += time.time() - t0
        self.n_run += 1
        return pd.DataFrame(rows, columns=cols)

    def validate(self, sql: str, db: str) -> Tuple[bool, str, List[str]]:
        conn = self._conn(db)
        try:
            with conn.cursor() as c:
                c.execute(f"SELECT * FROM (\n{sql}\n) AS _v LIMIT 5")
                cols = [d.name for d in c.description] if c.description else []
                c.fetchall()
            return True, "ok", cols
        except Exception as e:  # noqa: BLE001
            self._conn(db).rollback() if not conn.autocommit else None
            return False, f"{type(e).__name__}: {e}"[:200], []

    def close(self):
        for c in self.conns.values():
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass


_SCHEMA_CACHE: Dict[str, str] = {}


def render_pg_schema(client: PGClient, db: str) -> str:
    if db in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[db]
    schema = SCIENCE_DBS[db]["schema"]
    conn = client._conn(db)
    with conn.cursor() as c:
        c.execute(
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns WHERE table_schema=%s "
            "ORDER BY table_name, ordinal_position", (schema,))
        rows = c.fetchall()
        # primary keys
        c.execute(
            "SELECT tc.table_name, kcu.column_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name "
            "AND tc.table_schema=kcu.table_schema WHERE tc.constraint_type='PRIMARY KEY' "
            "AND tc.table_schema=%s", (schema,))
        pks = {(t, col) for t, col in c.fetchall()}
    by_tbl: Dict[str, List[tuple]] = {}
    for t, col, dtype in rows:
        by_tbl.setdefault(t, []).append((col, dtype))
    blocks = []
    for t, cols in by_tbl.items():
        lines = [f"CREATE TABLE {t} ("]
        coldefs = [f"  {col} {dtype}{' PRIMARY KEY' if (t, col) in pks else ''}" for col, dtype in cols]
        lines.append(",\n".join(coldefs))
        lines.append(");")
        blocks.append("\n".join(lines))
    out = "\n\n".join(blocks)
    _SCHEMA_CACHE[db] = out
    return out


def load_science_tasks(benchmarks: List[str], limit: int) -> List[Dict]:
    tasks = []
    for b in benchmarks:
        path = os.path.join(SCIENCE_ROOT, b, "dev.json")
        if not os.path.exists(path):
            print(f"  (no dev.json for {b})")
            continue
        data = json.load(open(path))
        if limit:
            data = data[:limit]
        for i, r in enumerate(data):
            gold = r.get("query") or r.get("sql")
            if not isinstance(gold, str):
                continue
            tasks.append({"instance_id": f"{b}_{i}", "db": b, "question": str(r["question"]),
                          "gold_sql": gold, "evidence": ""})
    return tasks


# --------------------------------------------------------------------------- #
# Execution-match scoring
# --------------------------------------------------------------------------- #
def _canon(df: pd.DataFrame) -> Counter:
    def cell(x):
        if isinstance(x, float):
            return "NULL" if math.isnan(x) else round(x, 4)
        return "NULL" if x is None else str(x)
    return Counter(tuple(cell(v) for v in row) for row in df.itertuples(index=False, name=None))


def score(client: PGClient, pred_df: Optional[pd.DataFrame], t: Dict) -> Tuple[bool, str]:
    if pred_df is None:
        return False, "no pred"
    try:
        gold_df = client.run(t["gold_sql"], t["db"])
    except Exception as e:  # noqa: BLE001
        return False, f"gold failed: {type(e).__name__}: {e}"[:160]
    if pred_df.shape[1] != gold_df.shape[1]:
        return False, f"col count {pred_df.shape[1]} != gold {gold_df.shape[1]}"
    return (_canon(pred_df) == _canon(gold_df)), ("" if _canon(pred_df) == _canon(gold_df) else "mismatch")


# --------------------------------------------------------------------------- #
# PostgreSQL-dialect generation
# --------------------------------------------------------------------------- #
VIEW_SYS = ("You build ONE reusable PostgreSQL CTE body: a single SELECT (no `WITH` wrapper, no "
            "trailing `;`). " + PG_RULES + " Lift question-specific literals OUT of the view. "
            "Output one ```sql block then one ```json metadata block.")
VIEW_USER = """PostgreSQL schema (DDL):
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

FINAL_SYS = ("You are the PostgreSQL generator. The listed views are ALREADY DEFINED as CTEs (do not "
             "redefine them). Write ONLY the final SELECT answering the question. " + PG_RULES +
             " Apply the question-specific filters/ordering/limit here. Output one ```sql block.")
FINAL_USER = """PostgreSQL schema:
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

DIRECT_SYS = ("You are a PostgreSQL generator. Output one ```sql block with a single executable "
              "query. " + PG_RULES + " No explanation.")
DIRECT_USER = """PostgreSQL schema (DDL):
{schema}

Question: {question}
{evidence}{error}
```sql
SELECT ...
```"""

REVISE_SYS = ("You are the SQL revisor. Fix the PostgreSQL query so it executes and answers the "
              "question. " + PG_RULES + " Output one corrected ```sql block only.")
REVISE_USER = """PostgreSQL schema (DDL):
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

SEM_SYS = ("You are the Revisor performing a final semantic check on a PostgreSQL query. Given a "
           "query that already executes, verify it truly answers the intent (correct columns, "
           "filters, aggregation, ordering/limit). If correct, return it unchanged. Otherwise "
           "return a corrected query. " + PG_RULES + " Output one ```sql block only.")
SEM_USER = """PostgreSQL schema (DDL):
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


def gen_view(llm, schema, req, existing) -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = ("You MAY build on these existing views (SELECT FROM them, list in depends_on):\n"
              + "\n".join(f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]) + "\n")
    txt = llm.ask(VIEW_SYS, VIEW_USER.format(schema=schema[:14000], name=req.want_name,
                  category=req.category, desc=req.text, outs=req.required_outputs,
                  grain=req.required_grain, existing=ex, error=""), tag="sc_view", max_tokens=1400)
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


def compose_final(llm, schema, question, evidence, chosen, plan) -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}" for v in chosen)
    txt = llm.ask(FINAL_SYS, FINAL_USER.format(schema=schema[:12000], views=vs, question=question,
                  evidence=evidence, plan=plan), tag="sc_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def gen_direct(llm, schema, question, evidence, prior_error=None) -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema[:14000], question=question,
                  evidence=evidence, error=err), tag="sc_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def revise(llm, schema, question, evidence, sql, error) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(REVISE_SYS, REVISE_USER.format(schema=schema[:14000], question=question,
                  evidence=ev, sql=sql, error=error), tag="sc_revise", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


def semantic_revise(llm, schema, rewrite_text, question, evidence, sql, preview) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(SEM_SYS, SEM_USER.format(schema=schema[:12000], rewrite=rewrite_text,
                  question=question, evidence=ev, sql=sql, preview=preview),
                  tag="sc_semantic", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


def validate_view(client: PGClient, registry: SkillRegistry, spec: ViewSpec, db: str) -> Tuple[bool, str]:
    try:
        dep_specs = registry.topo_closure(spec.depends_on) if spec.depends_on else []
        chosen = {s.name: s for s in dep_specs}
        chosen[spec.name] = spec
        ordered = sqlview._order_specs(list(chosen.values()))
        with_clause = ",\n".join(s.cte_clause() for s in ordered)
        prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
        sql = f"{prefix} {with_clause}\nSELECT * FROM {spec.name} LIMIT 5"
        ok, err, cols = client.validate(sql, db)
        if not ok:
            return False, err
        low = {c.lower() for c in cols}
        missing = [c for c in spec.output_columns if c.lower() not in low]
        return (not missing), ("ok" if not missing else f"declared outputs missing: {missing}")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _save(tag, rows, client, verify, registries=None):
    out = os.path.join(RESULTS_DIR, f"{tag}_science.json")
    n = max(1, len(rows))
    json.dump({"verify": verify, "n": len(rows), "n_ok": sum(r["correct"] for r in rows),
               "accuracy": round(sum(r["correct"] for r in rows) / n, 4),
               "reuse": sum(r["reused"] for r in rows), "gen": sum(r["generated"] for r in rows),
               "seed_reuse": sum(r.get("seed_reused", 0) for r in rows),
               "negative_reuse_nontrivial": sum(r.get("negative_reuse", False) for r in rows),
               "pg_exec_seconds": round(client.exec_seconds, 1), "pg_n_run": client.n_run,
               "rows": rows, "llm_usage": USAGE.snapshot()}, open(out, "w"), indent=2)
    if registries:
        from dataclasses import asdict
        gdump = {db: {"views": {nm: asdict(v) for nm, v in g.views.items()}, "n_views": g.n_views()}
                 for db, g in registries.items()}
        json.dump(gdump, open(os.path.join(RESULTS_DIR, f"{tag}_science_registrys.json"), "w"), indent=2)
    return out


def _init_registry(db: str, seed_dir: str) -> Tuple[SkillRegistry, set]:
    if seed_dir:
        sp = os.path.join(seed_dir, f"{db}.json")
        if os.path.exists(sp):
            g = sqlview.load_registry(sp)
            return g, set(g.views.keys())
    return SkillRegistry(db_id=db), set()


def _filter_runnable_gold(client: PGClient, tasks: List[Dict]) -> List[Dict]:
    keep = []
    for t in tasks:
        try:
            client.run(t["gold_sql"], t["db"])
            keep.append(t)
        except Exception:  # noqa: BLE001
            pass
    dropped = len(tasks) - len(keep)
    if dropped:
        print(f"  [gold filter] kept {len(keep)}/{len(tasks)} (dropped {dropped} non-executing gold)")
    return keep


def run(benchmarks, limit, verify, max_views, model, tag, seed_dir=""):
    tasks = load_science_tasks(benchmarks, limit)
    client = PGClient()
    tasks = _filter_runnable_gold(client, tasks)
    llm = LLM(model=model)
    _ = Embedder()
    registries: Dict[str, SkillRegistry] = {}
    seed_names: Dict[str, set] = {}
    rows = []
    cfg = "S(seed)" if seed_dir else ("A" if verify > 0 else "B")
    print(f"ScienceBench run [{cfg}]: {len(tasks)} tasks | dbs={benchmarks} verify={verify} "
          f"seed_dir={seed_dir or '-'}\n")
    for ti, t in enumerate(tasks):
        if ti and ti % 20 == 0:
            _save(tag, rows, client, verify, registries)
        db = t["db"]
        schema = render_pg_schema(client, db)
        ev = t.get("evidence", "")
        if verify <= 0:
            registries[db] = SkillRegistry(db_id=db)
        elif db not in registries:
            registries[db], seed_names[db] = _init_registry(db, seed_dir)
        g = registries.setdefault(db, SkillRegistry(db_id=db))
        sn = seed_names.get(db, set())

        _rw, rw = agents.rewrite_question(llm, schema, t["question"], ev)
        reqs, _raw, _sel = agents.propose_views(llm, schema, rw, max_views=max_views)

        chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
        reused_names, reused_specs = [], []
        for req in reqs:
            spec = None
            cands = sqlview.retrieve_candidates(g, req, embedder=None, k=6) if verify > 0 else []
            if cands:
                picks = [agents.choose_reuse(llm, req, cands) for _ in range(verify)]
                names = [p[0] for p in picks if p[0]]
                if names:
                    top, cnt = Counter(names).most_common(1)[0]
                    if cnt * 2 > verify:
                        spec = next(c for c in cands if c.name == top)
                if spec is None:
                    vrej += 1
            if spec is not None:
                chosen.append(spec); reused += 1
                reused_names.append(spec.name); reused_specs.append(spec)
                if spec.name in sn:
                    seed_reused += 1
                continue
            cand = gen_view(llm, schema, req, list(g.views.values()))
            if cand is None:
                continue
            if g.has(cand.name):
                cand.name = f"{cand.name}_{len(g.views)}"
            g.add_view(cand)
            ok, _vmsg = validate_view(client, g, cand, db)
            if ok:
                chosen.append(cand); gen += 1
            else:
                g.remove_view(cand.name)

        composed, plan = None, None
        if chosen:
            plan = agents.planner(llm, schema, rw, chosen)
            final = compose_final(llm, schema, t["question"], ev, chosen, plan)
            if final:
                try:
                    composed = compose_sql(g, [v.name for v in chosen], final)
                except Exception:  # noqa: BLE001
                    composed = None
        if composed is None:
            composed = gen_direct(llm, schema, t["question"], ev)

        df, err = None, "no sql"
        for attempt in range(SQL_REPAIR_ATTEMPTS):
            if not composed:
                break
            try:
                df = client.run(composed, db)
                err = ""
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                df = None
                if attempt < SQL_REPAIR_ATTEMPTS - 1:
                    composed = revise(llm, schema, t["question"], ev, composed, err) or composed

        if df is not None and composed:
            preview = str(df.head(3).values.tolist())[:300]
            sem = semantic_revise(llm, schema, rw, t["question"], ev, composed, preview)
            if sem and sem.strip() != composed.strip():
                try:
                    df2 = client.run(sem, db)
                    composed, df = sem, df2
                except Exception:  # noqa: BLE001
                    pass

        correct, serr = score(client, df, t)
        correct_b = bool(correct)
        used_nontrivial = any(not sqlview.is_trivial_projection(s) for s in reused_specs)
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
                     "verify_reject": vrej, "registry_views": g.n_views(), "seed_views": len(sn),
                     "used_reuse": reused > 0, "negative_reuse": bool(used_nontrivial and not correct_b),
                     "error": err or serr, "question": t["question"], "pred_sql": composed})
        print(f"  {t['instance_id']:12} {db[:8]:8} ok={int(correct_b)} reuse={reused}"
              f"(seed={seed_reused}) gen={gen} vrej={vrej} registry={g.n_views()} "
              f"{('' if correct_b else (err or serr)[:40])}", flush=True)

    n_ok = sum(r["correct"] for r in rows)
    print(f"\n=== ScienceBench summary [{cfg}] === tasks {len(rows)} | correct {n_ok} "
          f"({100*n_ok/max(1,len(rows)):.1f}%) | reuse {sum(r['reused'] for r in rows)} "
          f"(seed {sum(r['seed_reused'] for r in rows)}) | gen {sum(r['generated'] for r in rows)} | "
          f"neg-reuse {sum(r['negative_reuse'] for r in rows)}")
    out = _save(tag, rows, client, verify, registries)
    print(f"  wrote {out}")
    client.close()


def main():
    ap = argparse.ArgumentParser(description="Run SkiewSQL (A/B/S) on ScienceBenchmark (PostgreSQL).")
    ap.add_argument("--dbs", default="cordis", help="comma list: cordis,oncomx,sdss")
    ap.add_argument("--limit", type=int, default=40, help="max dev questions per db")
    ap.add_argument("--verify", type=int, default=3, help="reuse voters. 0 = config B (no reuse)")
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="science")
    ap.add_argument("--seed_dir", default="", help="config S: dir of frozen seed registries ({db}.json)")
    args = ap.parse_args()
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()]
    run(dbs, args.limit, args.verify, args.max_views, args.model, args.tag, seed_dir=args.seed_dir)


if __name__ == "__main__":
    main()
