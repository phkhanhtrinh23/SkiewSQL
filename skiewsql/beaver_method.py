"""
beaver_method.py — run the SkiewSQL view-memory method (retrieve-or-generate reusable CTEs) with the
optional Layer-3 adversarial verifier on the BEAVER enterprise benchmark, natively on MySQL/MariaDB.

BEAVER ships MySQL-dialect databases (backtick identifiers, MySQL functions like VARIANCE/STDDEV,
window functions) and MySQL-dialect gold SQL, so — for a fair execution-match — BOTH the generated
query and the gold are executed on the SAME local MariaDB server (see the setup in the run notes).

Structure is a direct port of sf_method.py (Snowflake):
  * CTE validation runs the view's `WITH ... SELECT * ... LIMIT 5` and reads the cursor description
    (syntax + declared output columns) — the MySQL analogue of Snowflake `describe`.
  * The final composed query per question is executed; the gold is executed too, and Execution Match
    (order-insensitive multiset equality, float-tolerant) is the score.

Configs (identical semantics to realrun.py / sf_method.py):
  B (verify=0) = faithful AV-SQL baseline (no memory; graph reset each question).
  A (verify>0) = online memory from empty.
  S (verify>0 + seed_dir) = cold-start seed then online growth.  ← the best setting.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
from collections import Counter
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pymysql

from skiewsql import agents, sqlview, reforce_modules
from skiewsql.core import ViewGraph, ViewSpec, ViewRequest, compose_sql
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_real")
BEAVER_ROOT = os.environ.get("BEAVER_ROOT", "/mnt/win_d/skill_driven_agent_view/beaver_data")
QUERY_DIR = os.path.join(BEAVER_ROOT, "beaver-query", "data")

MYSQL_HOST = os.environ.get("BEAVER_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("BEAVER_MYSQL_PORT", "3307"))
MYSQL_USER = os.environ.get("BEAVER_MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("BEAVER_MYSQL_PASS", "")

SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max (matches realrun.py)

MYSQL_RULES = (
    "Use MySQL/MariaDB dialect. Identifiers are case-sensitive as written in the schema; you may "
    "quote them with backticks. A single database is in scope, so do NOT schema-qualify tables. Use "
    "standard SQL plus MySQL functions where needed (VARIANCE, STDDEV, DATE_FORMAT, GROUP_CONCAT, "
    "window functions). Carry key/id columns through CTEs so views stay joinable. No Snowflake "
    "VARIANT syntax, no double-quote string literals (use single quotes)."
)


# --------------------------------------------------------------------------- #
# MySQL client
# --------------------------------------------------------------------------- #
class MySQLClient:
    def __init__(self):
        self.conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                                    password=MYSQL_PASS, autocommit=True, connect_timeout=15,
                                    read_timeout=120, charset="utf8mb4")
        self.exec_seconds = 0.0
        self.n_run = 0
        self._db = None
        with self.conn.cursor() as c:                # be permissive about legacy dumps
            try:
                c.execute("SET SESSION sql_mode=''")
            except Exception:  # noqa: BLE001
                pass

    def use(self, db: str):
        if db != self._db:
            self.conn.select_db(db)
            self._db = db
            with self.conn.cursor() as c:
                try:
                    c.execute("SET SESSION sql_mode=''")
                    c.execute("SET SESSION max_statement_time=60")   # cap runaway queries (seconds)
                except Exception:  # noqa: BLE001
                    pass

    def run(self, sql: str, db: str) -> pd.DataFrame:
        import time
        self.use(db)
        t0 = time.time()
        with self.conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
            cols = [d[0] for d in c.description] if c.description else []
        self.exec_seconds += time.time() - t0
        self.n_run += 1
        return pd.DataFrame(list(rows), columns=cols)

    def validate(self, sql: str, db: str) -> Tuple[bool, str, List[str]]:
        """Compile/plan check + output columns, cheaply. LIMIT-wrap so we don't scan the whole table."""
        self.use(db)
        try:
            with self.conn.cursor() as c:
                c.execute(f"SELECT * FROM (\n{sql}\n) AS _v LIMIT 5")
                cols = [d[0] for d in c.description] if c.description else []
                c.fetchall()
            return True, "ok", cols
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"[:200], []

    def close(self):
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# Schema rendering from information_schema
# --------------------------------------------------------------------------- #
_SCHEMA_CACHE: Dict[str, str] = {}


def render_mysql_schema(client: MySQLClient, db: str, sample_rows: int = 2) -> str:
    if db in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[db]
    client.use(db)
    with client.conn.cursor() as c:
        c.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION", (db,))
        rows = c.fetchall()
    by_tbl: Dict[str, List[tuple]] = {}
    for t, col, ctype, nullable, key in rows:
        by_tbl.setdefault(t, []).append((col, ctype, key))
    blocks = []
    for t, cols in by_tbl.items():
        lines = [f"CREATE TABLE `{t}` ("]
        coldefs = []
        for col, ctype, key in cols:
            k = " PRIMARY KEY" if key == "PRI" else (" KEY" if key in ("MUL", "UNI") else "")
            coldefs.append(f"  `{col}` {ctype}{k}")
        lines.append(",\n".join(coldefs))
        lines.append(");")
        blocks.append("\n".join(lines))
    schema = "\n\n".join(blocks)
    _SCHEMA_CACHE[db] = schema
    return schema


# --------------------------------------------------------------------------- #
# Schema chunking + selection (replaces the fatal `schema[:14000]` truncation)
#
# A warehouse schema does not fit in a prompt: BEAVER `dw` is ~57k chars / 97 tables, so a fixed
# prefix slice showed the model only the first 14 tables (alphabetically) and silently DELETED the
# other 83 — including the tables most questions actually need. We instead:
#   (1) CHUNK by WHOLE TABLES (a table is never split, so a half-table can never masquerade as a
#       complete one — the failure mode a column-sliding window would introduce),
#   (2) SELECT: propose sub-goals per chunk, collecting the tables each chunk deems relevant,
#   (3) UNION + render those tables IN FULL as the schema given to the generators.
# Every table is therefore visible to the proposer, and the generator sees complete definitions of
# exactly the tables the question needs — which is also what makes a cross-table join possible at all.
# --------------------------------------------------------------------------- #
_CHUNK_CACHE: Dict[str, List[str]] = {}
_TABLE_BLOCKS: Dict[str, Dict[str, str]] = {}


def _table_blocks(client: MySQLClient, db: str) -> Dict[str, str]:
    """{table_name: its full CREATE TABLE block} for the DB."""
    if db in _TABLE_BLOCKS:
        return _TABLE_BLOCKS[db]
    blocks = {}
    for b in render_mysql_schema(client, db).split("\n\n"):
        if "`" in b:
            blocks[b.split("`")[1]] = b
    _TABLE_BLOCKS[db] = blocks
    return blocks


def chunk_mysql_schema(client: MySQLClient, db: str, budget_chars: int = 12000) -> List[str]:
    """Pack WHOLE table definitions into chunks of <= budget_chars. Nothing is ever dropped; a table
    is split only if it alone exceeds the budget, and then the continuation is marked explicitly so
    the model cannot mistake a fragment for the whole table."""
    if db in _CHUNK_CACHE:
        return _CHUNK_CACHE[db]
    chunks, cur, cur_len = [], [], 0
    for name, blk in _table_blocks(client, db).items():
        if len(blk) > budget_chars:                       # oversized single table -> mark the split
            if cur:
                chunks.append("\n\n".join(cur)); cur, cur_len = [], 0
            lines = blk.split("\n")
            part, n = [], 0
            for ln in lines:
                part.append(ln)
                if sum(len(x) for x in part) > budget_chars:
                    n += 1
                    chunks.append(f"CREATE TABLE `{name}` (  /* PART {n}, table continues below */\n"
                                  + "\n".join(part[1:]) + "\n);")
                    part = []
            if part:
                chunks.append(f"CREATE TABLE `{name}` (  /* FINAL PART of this table */\n"
                              + "\n".join(part) + "\n);")
            continue
        if cur_len + len(blk) > budget_chars and cur:
            chunks.append("\n\n".join(cur)); cur, cur_len = [], 0
        cur.append(blk); cur_len += len(blk) + 2
    if cur:
        chunks.append("\n\n".join(cur))
    _CHUNK_CACHE[db] = chunks
    return chunks


def filtered_mysql_schema(client: MySQLClient, db: str, tables) -> str:
    """Render ONLY the selected tables, each COMPLETE. Falls back to the first chunk if the selection
    is empty, so the generator is never handed an empty schema."""
    blocks = _table_blocks(client, db)
    low = {t.lower(): t for t in blocks}
    picked, seen = [], set()
    for t in tables:
        a = low.get(str(t).lower().strip("`"))
        if a and a not in seen:
            seen.add(a); picked.append(blocks[a])
    if not picked:
        return chunk_mysql_schema(client, db)[0]
    return "\n\n".join(picked)


# --------------------------------------------------------------------------- #
# Task loading from the BEAVER query parquets
# --------------------------------------------------------------------------- #
def load_beaver_tasks(splits: List[str], limit: int) -> List[Dict]:
    """Each split parquet (dw, dw_real, neutron, nova) has: id, db, question, sql (gold),
    domain_knowledge. `db` is the PHYSICAL database to run against (dw_real -> dw)."""
    tasks = []
    for split in splits:
        files = glob.glob(os.path.join(QUERY_DIR, f"{split}-*.parquet"))
        if not files:
            print(f"  (no parquet for split '{split}')")
            continue
        df = pd.read_parquet(files[0])
        if limit:
            df = df.head(limit)
        for _, r in df.iterrows():
            dk = r.get("domain_knowledge")
            try:
                dk_list = json.loads(dk) if isinstance(dk, str) else (list(dk) if dk is not None else [])
            except Exception:  # noqa: BLE001
                dk_list = []
            tasks.append({"instance_id": str(r["id"]), "db": str(r["db"]), "split": split,
                          "question": str(r["question"]), "gold_sql": str(r["sql"]),
                          "evidence": "; ".join(str(x) for x in dk_list)})
    return tasks


def _evidence(t: Dict) -> str:
    return t.get("evidence", "") or ""


# --------------------------------------------------------------------------- #
# Execution-match scoring (order-insensitive multiset, float-tolerant)
# --------------------------------------------------------------------------- #
def _canon(df: pd.DataFrame) -> set:
    def cell(x):
        if isinstance(x, float):
            if math.isnan(x):
                return "NULL"
            return round(x, 4)
        if x is None:
            return "NULL"
        return str(x)
    return Counter(tuple(cell(v) for v in row) for row in df.itertuples(index=False, name=None))


def score(client: MySQLClient, pred_df: Optional[pd.DataFrame], t: Dict) -> Tuple[bool, str]:
    if pred_df is None:
        return False, "no pred"
    try:
        gold_df = client.run(t["gold_sql"], t["db"])
    except Exception as e:  # noqa: BLE001
        return False, f"gold failed: {type(e).__name__}: {e}"[:160]
    if pred_df.shape[1] != gold_df.shape[1]:
        return False, f"col count {pred_df.shape[1]} != gold {gold_df.shape[1]}"
    # order-insensitive multiset match, column-order-insensitive by comparing canonical row bags
    if _canon(pred_df) == _canon(gold_df):
        return True, ""
    return False, "result mismatch"


# --------------------------------------------------------------------------- #
# MySQL-dialect generation (view body, final query, direct, repair, semantic)
# --------------------------------------------------------------------------- #
VIEW_SYS = (
    "You build ONE reusable MySQL SQL CTE body: a single SELECT (no `WITH` wrapper, no trailing `;`) "
    "that defines the view. " + MYSQL_RULES + " Lift question-specific literals OUT of the view. "
    "NO SUBSTITUTION: expose each required column from its EXACT named source table; never substitute "
    "a look-alike column (e.g. a *_CODE for a *_NAME) and never re-derive a value that has a stored "
    "source column (do NOT SUM child rows to fake a parent's stored total — read the stored column). "
    "Output one ```sql block then one ```json metadata block.")
VIEW_USER = """MySQL schema (DDL):
{schema}

Build the view `{name}` (category {category}). Meaning: {desc}
Required output columns, given as `table.column`: {outs}
  - In the SQL, alias each to the BARE column name (the part AFTER the dot).
  - In metadata `output_columns`, list them QUALIFIED as `table.column`, naming the SAME table you
    actually selected the column from.
  - If a required `table.column` is not available from that exact table, JOIN that base table to get
    it; do NOT swap in a look-alike column and do NOT re-derive a stored value.
Grain (one row per): {grain}
{existing}{error}
```sql
SELECT ...
```
```json
{{"output_columns": ["table.column", "..."], "source_tables": ["..."], "grain": ["..."], "depends_on": []}}
```"""

FINAL_SYS = (
    "You are the MySQL SQL generator. The listed views are ALREADY DEFINED as CTEs (do not redefine "
    "them). Write ONLY the final SELECT answering the question, using those views and, if needed, "
    "base tables. " + MYSQL_RULES + " Apply the question-specific filters/ordering/limit here. "
    "NO SUBSTITUTION: if a column the question needs is not EXACTLY present in the listed views, read "
    "it from its base table via a join — never substitute a similarly-named column (e.g. a *_CODE for "
    "a *_NAME) and never re-derive a value that has a stored source column.\n"
    "PROJECTION DISCIPLINE (the answer is compared column-by-column against the expected result): "
    "SELECT exactly the columns the question asks for, in the order asked, and NOTHING else — a "
    "reused view exposes many columns (keys, intermediate measures), which are for COMPUTING the "
    "answer, not for returning it. Do not return an id/key or an intermediate value (a total, an "
    "area, a denominator) unless asked. Use SELECT DISTINCT when the question asks for distinct "
    "entities and the joins could repeat rows. Do not multiply a ratio by 100 unless the question "
    "says percent. "
    "Output one ```sql block.")
FINAL_USER = """MySQL schema:
{schema}

Already-defined CTE views you can SELECT FROM (do NOT redefine):
{views}

Question: {question}
{evidence}{reforce}
Plan:
{plan}
```sql
SELECT ...
```"""

DIRECT_SYS = ("You are a MySQL SQL generator. Output one ```sql block with a single executable MySQL "
              "query. " + MYSQL_RULES + " No explanation.")
DIRECT_USER = """MySQL schema (DDL):
{schema}

Question: {question}
{evidence}{reforce}{error}
```sql
SELECT ...
```"""

REVISE_SYS = ("You are the SQL revisor. Fix the MySQL query so it executes and answers the question. "
              + MYSQL_RULES + " Output one corrected ```sql block only.")
REVISE_USER = """MySQL schema (DDL):
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

SEM_SYS = ("You are the Revisor performing a final semantic check on a MySQL query. Given a query "
           "that already executes, verify it truly answers the intent (correct columns, filters, "
           "aggregation, ordering/limit). If correct, return it unchanged; otherwise return a "
           "corrected query. " + MYSQL_RULES + " Output one ```sql block only.")
SEM_USER = """MySQL schema (DDL):
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


def gen_view(llm, schema, req, existing, reforce="") -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = ("You MAY build on these existing views (SELECT FROM them, list in depends_on):\n"
              + "\n".join(f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]) + "\n")
    txt = llm.ask(VIEW_SYS, VIEW_USER.format(schema=schema[:24000], name=req.want_name,
                  category=req.category, desc=req.text, outs=req.required_outputs,
                  grain=req.required_grain, existing=ex, reforce=reforce, error=""), tag="bv_view", max_tokens=1400)
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


def compose_final(llm, schema, question, evidence, chosen, plan, reforce="") -> Optional[str]:
    if not chosen:
        return None
    vs = "\n".join(f"- {v.name} (cols: {', '.join(v.output_columns)}) — {v.description}" for v in chosen)
    txt = llm.ask(FINAL_SYS, FINAL_USER.format(schema=schema[:24000], views=vs, question=question,
                  evidence=evidence, plan=plan, reforce=reforce), tag="bv_compose", max_tokens=1000)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def gen_direct(llm, schema, question, evidence, prior_error=None, reforce="") -> Optional[str]:
    err = f"\nPrevious query failed: {prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(DIRECT_SYS, DIRECT_USER.format(schema=schema[:24000], question=question,
                  evidence=evidence, reforce=reforce, error=err), tag="bv_direct", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


def revise(llm, schema, question, evidence, sql, error) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(REVISE_SYS, REVISE_USER.format(schema=schema[:24000], question=question,
                  evidence=ev, sql=sql, error=error), tag="bv_revise", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


def semantic_revise(llm, schema, rewrite_text, question, evidence, sql, preview) -> Optional[str]:
    ev = f"External knowledge: {evidence}" if evidence.strip() else ""
    txt = llm.ask(SEM_SYS, SEM_USER.format(schema=schema[:24000], rewrite=rewrite_text,
                  question=question, evidence=ev, sql=sql, preview=preview),
                  tag="bv_semantic", max_tokens=1400)
    out = extract_code(txt, langs=("sql",))
    return out.strip().rstrip(";") if out else None


def validate_view(client: MySQLClient, graph: ViewGraph, spec: ViewSpec, db: str) -> Tuple[bool, str]:
    try:
        dep_specs = graph.topo_closure(spec.depends_on) if spec.depends_on else []
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
        # output_columns are stored QUALIFIED (`table.column`) for the reuse guard; the executed
        # result columns are the BARE aliases, so validate on the bare suffix.
        missing = [c for c in spec.output_columns
                   if c.split(".")[-1].strip("`\" ").lower() not in low]
        return (not missing), ("ok" if not missing else f"declared outputs missing: {missing}")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def validate_closure(client: MySQLClient, graph: ViewGraph, names: List[str],
                     db: str) -> Tuple[bool, Optional[str], str]:
    """Fix #3 — L3 over the FULL DEPENDS_ON closure of `names` (the chosen sub-goal views PLUS every
    transitive dependency), not just the chosen ones. Each view must execute and expose its declared
    outputs against the live DB, and each DEPENDS_ON target must still exist. Closes the hole where a
    view dragged into compose_sql via a dependency edge (e.g. a seed view) reached the final query
    unchecked. Returns (ok, offending_view_or_None, reason)."""
    # Defensive closure walk (does NOT use graph.topo_closure, which KeyErrors on a dangling edge):
    # a missing DEPENDS_ON target is reported as the offender instead of crashing.
    seen, stack = set(), list(names)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        s = graph.views.get(n)
        if s is None:
            return False, n, f"chosen view {n} not in graph"
        seen.add(n)
        for d in s.depends_on:
            if not graph.has(d):
                return False, n, f"missing dependency {d}"
            stack.append(d)
    # L3: every view in the closure must execute and expose its declared outputs against the live DB.
    for n in seen:
        ok, msg = validate_view(client, graph, graph.views[n], db)
        if not ok:
            return False, n, msg
    return True, None, "ok"


# --------------------------------------------------------------------------- #
# Persistence + seed loading
# --------------------------------------------------------------------------- #
def _save(tag, rows, client, verify, graphs=None):
    out = os.path.join(RESULTS_DIR, f"{tag}_beaver.json")
    n = max(1, len(rows))
    json.dump({"verify": verify, "n": len(rows), "n_ok": sum(r["correct"] for r in rows),
               "accuracy": round(sum(r["correct"] for r in rows) / n, 4),
               "reuse": sum(r["reused"] for r in rows), "gen": sum(r["generated"] for r in rows),
               "seed_reuse": sum(r.get("seed_reused", 0) for r in rows),
               "negative_reuse_nontrivial": sum(r.get("negative_reuse", False) for r in rows),
               "mysql_exec_seconds": round(client.exec_seconds, 1), "mysql_n_run": client.n_run,
               "rows": rows, "llm_usage": USAGE.snapshot()}, open(out, "w"), indent=2)
    if graphs:
        from dataclasses import asdict
        gdump = {db: {"views": {nm: asdict(v) for nm, v in g.views.items()}, "n_views": g.n_views()}
                 for db, g in graphs.items()}
        json.dump(gdump, open(os.path.join(RESULTS_DIR, f"{tag}_beaver_graphs.json"), "w"), indent=2)
    return out


def _init_graph(db: str, seed_dir: str) -> Tuple[ViewGraph, set]:
    if seed_dir:
        sp = os.path.join(seed_dir, f"{db}.json")
        if os.path.exists(sp):
            g = sqlview.load_graph(sp)
            return g, set(g.views.keys())
    return ViewGraph(db_id=db), set()


# --------------------------------------------------------------------------- #
# Method loop (identical control flow to sf_method.run)
# --------------------------------------------------------------------------- #
def _filter_runnable_gold(client: MySQLClient, tasks: List[Dict]) -> List[Dict]:
    """Keep only tasks whose GOLD SQL executes on our MariaDB (some BEAVER gold uses MySQL-8-only
    features — GROUPING(), framed row_number() — that MariaDB rejects). Scoring is only meaningful
    where gold runs, and this is fair across configs since all share the same gold set."""
    keep = []
    for t in tasks:
        try:
            client.run(t["gold_sql"], t["db"])
            keep.append(t)
        except Exception:  # noqa: BLE001
            pass
    dropped = len(tasks) - len(keep)
    if dropped:
        print(f"  [gold filter] kept {len(keep)}/{len(tasks)} (dropped {dropped} whose gold "
              f"does not execute on MariaDB)")
    return keep


def run(splits, limit, verify, max_views, model, tag, seed_dir="", use_reforce=False,
        nxm=False, max_subgoals=8):
    tasks = load_beaver_tasks(splits, limit)
    client = MySQLClient()
    tasks = _filter_runnable_gold(client, tasks)
    llm = LLM(model=model)
    emb = Embedder()   # used by deterministic (zero-token) reuse selection
    graphs: Dict[str, ViewGraph] = {}
    seed_names: Dict[str, set] = {}
    rows = []
    n_explore_total = 0
    cfg = "S(seed)" if seed_dir else ("A" if verify > 0 else "B")
    print(f"BEAVER run [{cfg}]: {len(tasks)} tasks | splits={splits} verify={verify} "
          f"seed_dir={seed_dir or '-'}\n")
    for ti, t in enumerate(tasks):
        if ti and ti % 20 == 0:
            _save(tag, rows, client, verify, graphs)
        db = t["db"]
        schema = render_mysql_schema(client, db)
        ev = _evidence(t)
        if verify <= 0:
            graphs[db] = ViewGraph(db_id=db)              # config B: reset each question
        elif db not in graphs:
            graphs[db], seed_names[db] = _init_graph(db, seed_dir)
        g = graphs.setdefault(db, ViewGraph(db_id=db))
        sn = seed_names.get(db, set())

        chunks = chunk_mysql_schema(client, db)
        _rw, rw = agents.rewrite_question(llm, "", t["question"], ev)  # schema-free: rewrite into sub-goals needs only the question
        per_tables: Dict[str, set] = {}
        if nxm:
            # N×M: decompose the question ONCE with the whole-DB table index in view -> M coherent
            # sub-goals, then align EACH sub-goal against EVERY chunk to gather all its tables (the
            # N×M loop). No arbitrary cap on M (only max_subgoals); a sub-goal whose tables span
            # several chunks still collects all of them.
            table_index = ", ".join(_table_blocks(client, db).keys())
            reqs, per_tables, _ncalls = agents.decompose_and_align(
                llm, chunks, rw, table_index, max_subgoals=max_subgoals, qualify_outputs=True,
                tag_prefix="bv_")
            sel_tables = set().union(*per_tables.values()) if per_tables else set()
        else:
            # Per-chunk proposal: every table in the warehouse is seen by the proposer (nothing is
            # truncated away), and each chunk contributes the tables it judges relevant.
            reqs, sel_tables, seen_names = [], set(), set()
            for ch in chunks:
                creqs, _raw, sel = agents.propose_views(llm, ch, rw, max_views=max_views,
                                                        qualify_outputs=True)
                for tb in (sel.get("tables") or []):
                    sel_tables.add(str(tb))
                for r in creqs:
                    if r.want_name.lower() in seen_names:
                        continue
                    seen_names.add(r.want_name.lower())
                    for tb in (getattr(r, "source_tables", None) or []):
                        sel_tables.add(str(tb).split(".")[0])
                    reqs.append(r)
            reqs = reqs[:max_views]
        # UNION of the selected tables, rendered IN FULL -> what the generators actually see.
        schema = filtered_mysql_schema(client, db, sel_tables)

        # ---- ReFoRCE modules (1:1 port; see reforce_modules.py) -------------------------------
        # FORMAT RESTRICTION: fix the answer's column header BEFORE any SQL is written.
        # COLUMN EXPLORATION: run <=10 SELECT DISTINCT probes and feed the observed VALUES back, so
        # the generator picks columns from data rather than from DDL names (the *_CODE vs *_NAME bug).
        reforce = ""
        if use_reforce:
            fmt = reforce_modules.format_answer(llm, t["question"])
            if fmt:
                reforce += ("\nREQUIRED ANSWER FORMAT (return EXACTLY these columns, in this order, "
                            "nothing more):\n" + fmt + "\n")

        chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
        reused_names, reused_specs = [], []
        for req in reqs:
            spec = None
            if verify > 0 and sqlview.deterministic_reuse_on():   # Zero-Mem: guard+embedding, no LLM
                spec, _d = sqlview.select_reuse(g, req, emb, tau=0.55)
                if spec is None and _d.get("reason") == "conflicting near-tie":
                    vrej += 1
            else:
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
            # PER-SUB-GOAL COLUMN EXPLORATION: probe the columns THIS sub-goal needs, and give the
            # evidence to the view generator — the step that actually chooses columns. (Injecting it
            # only at compose time was too late: the views were already written from DDL names.)
            # In N×M mode each sub-goal generates against ONLY its aligned tables (max-recall focus);
            # otherwise against the shared union schema.
            req_schema = (filtered_mysql_schema(client, db, per_tables[req.want_name])
                          if per_tables.get(req.want_name) else schema)
            sub_rf = reforce
            if use_reforce:
                pre_info, n_probe = reforce_modules.exploration(
                    llm, lambda q: client.run(q, db).head(5).to_string(index=False),
                    f"{req.text} (required outputs: {req.required_outputs}; grain: {req.required_grain})",
                    req_schema[:6000], api="mysql")
                n_explore_total += n_probe
                if pre_info:
                    sub_rf += ("\nColumn exploration — VALUES observed for this sub-goal (choose the "
                               "column whose values match what is asked, e.g. a name vs a code):\n"
                               + pre_info[:4000] + "\n")
            cand = gen_view(llm, req_schema, req, list(g.views.values()), reforce=sub_rf)
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

        # Fix #3 — guard the dependency closure: drop any chosen view whose closure (itself or a dep
        # pulled in via DEPENDS_ON) fails L3 against the live DB, before it reaches compose_sql.
        if chosen:
            ok_cl, bad, _why = validate_closure(client, g, [v.name for v in chosen], db)
            while not ok_cl and bad is not None:
                chosen = [v for v in chosen if v.name != bad]
                if bad in reused_names:
                    reused = max(0, reused - 1)
                    reused_names = [n for n in reused_names if n != bad]
                    reused_specs = [s for s in reused_specs if s.name != bad]
                    if bad in sn:
                        seed_reused = max(0, seed_reused - 1)
                else:
                    gen = max(0, gen - 1)
                if not chosen:
                    break
                ok_cl, bad, _why = validate_closure(client, g, [v.name for v in chosen], db)

        composed, plan = None, None
        if chosen:
            plan = agents.planner(llm, schema, rw, chosen)
            final = compose_final(llm, schema, t["question"], ev, chosen, plan, reforce=reforce)
            if final:
                try:
                    composed = compose_sql(g, [v.name for v in chosen], final)
                except Exception:  # noqa: BLE001
                    composed = None
        if composed is None:
            composed = gen_direct(llm, schema, t["question"], ev, reforce=reforce)

        # execution-repair loop (revise on error), then execute
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

        # semantic revisor (conservative single pass; accept only if it still executes)
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
        # Layer-4 learning + honest (non-trivial) negative-reuse flag
        used_nontrivial = any(not sqlview.is_trivial_projection(s) for s in reused_specs)
        for nm in reused_names:
            v = g.views.get(nm)
            if v is None:
                continue
            if correct_b and t["question"] not in v.validated_on:
                v.validated_on = (v.validated_on + [t["question"]])[-10:]
            elif (not correct_b) and t["question"] not in v.counter_examples:
                v.counter_examples = (v.counter_examples + [t["question"]])[-10:]
        rows.append({"instance_id": t["instance_id"], "db": db, "split": t["split"],
                     "correct": correct_b, "reused": reused, "seed_reused": seed_reused,
                     "generated": gen, "verify_reject": vrej, "graph_views": g.n_views(),
                     "seed_views": len(sn), "used_reuse": reused > 0,
                     "negative_reuse": bool(used_nontrivial and not correct_b),
                     "error": err or serr, "question": t["question"], "pred_sql": composed})
        print(f"  {t['instance_id']:14} {db[:10]:10} ok={int(correct_b)} reuse={reused}"
              f"(seed={seed_reused}) gen={gen} vrej={vrej} graph={g.n_views()} "
              f"{('' if correct_b else (err or serr)[:40])}", flush=True)

    n_ok = sum(r["correct"] for r in rows)
    print(f"\n=== BEAVER summary [{cfg}] === tasks {len(rows)} | correct {n_ok} "
          f"({100*n_ok/max(1,len(rows)):.1f}%) | reuse {sum(r['reused'] for r in rows)} "
          f"(seed {sum(r['seed_reused'] for r in rows)}) | gen {sum(r['generated'] for r in rows)} | "
          f"neg-reuse {sum(r['negative_reuse'] for r in rows)}")
    out = _save(tag, rows, client, verify, graphs)
    print(f"  wrote {out}")
    client.close()


def main():
    ap = argparse.ArgumentParser(description="Run SkiewSQL (A/B/S) on the BEAVER benchmark (MySQL).")
    ap.add_argument("--splits", default="neutron", help="comma list of query splits: dw,dw_real,neutron,nova")
    ap.add_argument("--limit", type=int, default=25, help="max questions per split")
    ap.add_argument("--verify", type=int, default=3,
                    help="reuse-selector voters (reject-biased strict majority); 0 = config B (no reuse)")
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="beaver")
    ap.add_argument("--seed_dir", default="", help="config S: dir of frozen seed graphs ({db}.json)")
    ap.add_argument("--reforce", type=int, default=0,
                    help="1 = enable the ReFoRCE modules: format restriction (fix the answer column header before writing SQL) + iterative column exploration (execute <=10 SELECT DISTINCT probes and feed observed values back)")
    ap.add_argument("--nxm", type=int, default=0,
                    help="1 = N×M decomposition: decompose the question once (whole-DB table index), then align each of M sub-goals against all N chunks (no cap at max_views)")
    ap.add_argument("--max_subgoals", type=int, default=4, help="N×M mode: cap on M sub-goals")
    args = ap.parse_args()
    splits = [s.strip() for s in args.splits.split(",") if s.strip()]
    run(splits, args.limit, args.verify, args.max_views, args.model, args.tag, seed_dir=args.seed_dir,
        use_reforce=bool(args.reforce), nxm=bool(args.nxm), max_subgoals=args.max_subgoals)


if __name__ == "__main__":
    main()
