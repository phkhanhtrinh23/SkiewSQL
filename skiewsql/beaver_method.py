"""beaver_method.py — run the SkiewSQL view-memory method (retrieve-or-generate reusable CTEs) with the optional Layer-3 adversarial verifier on the BEAVER enterprise benchmark, natively on MySQL/MariaDB. BEAVER ships MySQL-dialect databases (backtick identifiers, MySQL functions like VARIANCE/STDDEV, window functions) and MySQL-dialect gold SQL, so — for a fair execution-match — BOTH the generated query and the gold are executed on the SAME local MariaDB server (see the setup in the run notes).

Structure is a direct port of sf_method.py (Snowflake):
  * CTE validation runs the view's `WITH ... SELECT * ... LIMIT 5` and reads the cursor description (syntax + declared output columns) — the MySQL analogue of Snowflake `describe`.
  * The final composed query per question is executed. The gold is executed too, and Execution Match (order-insensitive multiset equality, float-tolerant) is the score.

Configs (identical semantics to realrun.py / sf_method.py): B (verify=0) = faithful AV-SQL baseline (no memory. Registry reset each question). A (verify>0) = online memory from empty. S (verify>0 + seed_dir) = cold-start seed then online growth.  ← the best setting."""
from __future__ import annotations
from skiewsql.prompt_loader import load_prompt

EXISTING_VIEWS = load_prompt("shared/existing_views.txt")

import argparse
import glob
import json
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pymysql

from skiewsql import agents, sqlview, valuelink
from skiewsql import avsql_prep, contracts, datasets
from skiewsql.core import SkillRegistry, ViewSpec, ViewRequest, compose_sql
import sys
from skiewsql.llm import LLM, Embedder, extract_code, extract_json, USAGE, DailyBudgetExhausted
from skiewsql.paths import BEAVER_RUNS_DIR, ensure_dir

RESULTS_DIR = ensure_dir(BEAVER_RUNS_DIR)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEAVER_ROOT = os.environ.get("BEAVER_ROOT", os.path.join(_PROJECT_ROOT, "data", "beaver"))
QUERY_DIR = os.path.join(BEAVER_ROOT, "beaver-query", "data")

MYSQL_HOST = os.environ.get("BEAVER_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("BEAVER_MYSQL_PORT", "3307"))
MYSQL_USER = os.environ.get("BEAVER_MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("BEAVER_MYSQL_PASS", "")

SQL_REPAIR_ATTEMPTS = 5          # AV-SQL T_max (matches realrun.py)

MYSQL_RULES = load_prompt("beaver_method/mysql_rules.txt")


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


# --------------------------------------------------------------------------- # Schema chunking + selection (replaces the fatal `schema[:14000]` truncation)
#
# A warehouse schema does not fit in a prompt: BEAVER `dw` is ~57k chars / 97 tables, so a fixed prefix slice showed the model only the first 14 tables (alphabetically) and silently DELETED the other 83 — including the tables most questions actually need. We instead: (1) CHUNK by WHOLE TABLES (a table is never split, so a half-table can never masquerade as a complete one — the failure mode a column-sliding window would introduce), (2) SELECT: propose sub-goals per chunk, collecting the tables each chunk deems relevant, (3) UNION + render those tables IN FULL as the schema given to the generators. Every table is therefore visible to the proposer, and the generator sees complete definitions of exactly the tables the question needs — which is also what makes a cross-table join possible at all. --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# AV-SQL preprocessing (avsql_prep.py), used unless SKIEW_SCHEMA_PREP=legacy
# --------------------------------------------------------------------------- #
AVSQL_CHUNK_TOKENS = 8000          # same token budget B as the SQLite runner (realrun.CHUNK_BUDGET)
VIEW_VALIDATE_ATTEMPTS = 3         # T_max, as in realrun
_AV_PREP: Dict[str, "avsql_prep.PreparedSchema"] = {}
_AV_VINDEX: Dict[str, "avsql_prep.AVSQLValueIndex"] = {}


def _mysql_rows(client: MySQLClient, db: str):
    def run(sql: str, params: tuple = ()) -> list:
        client.use(db)
        with client.conn.cursor() as c:
            c.execute(sql, params or None)
            return list(c.fetchall())
    return run


def avsql_prepared(client: MySQLClient, db: str) -> "avsql_prep.PreparedSchema":
    if db not in _AV_PREP:
        sd = avsql_prep.mysql_schema_dict(_mysql_rows(client, db), db)
        _AV_PREP[db] = avsql_prep.PreparedSchema(sd, AVSQL_CHUNK_TOKENS, datasets.est_tokens)
    return _AV_PREP[db]


def mysql_value_index(client: MySQLClient, db: str) -> "avsql_prep.AVSQLValueIndex":
    """Build the consolidated AV-SQL value index for MySQL and cache it by schema."""
    if db not in _AV_VINDEX:
        run = _mysql_rows(client, db)
        sd = avsql_prepared(client, db).schema_dict
        shape = json.dumps({t: [i["columns_name"], i["columns_type"]] for t, i in sorted(sd.items())})
        key = f"mysql:{MYSQL_HOST}:{MYSQL_PORT}:{db}:{shape}"
        _AV_VINDEX[db] = avsql_prep.load_or_build_index(key, lambda: avsql_prep.unique_values(
            sd, lambda t, c: [r[0] for r in run(f"SELECT DISTINCT `{c}` FROM `{t}` WHERE `{c}` IS NOT NULL")]))
    return _AV_VINDEX[db]


class _ColumnsCon:
    """What contracts.selection_consistency reads (`PRAGMA table_info`), answered from the MySQL schema dict."""

    def __init__(self, schema_dict: Dict[str, dict]):
        self.sd = {t.lower(): info for t, info in schema_dict.items()}

    def execute(self, sql: str):
        m = re.search(r'table_info\("(.+)"\)', sql)
        info = self.sd.get(m.group(1).lower()) if m else None
        rows = list(enumerate(info["columns_name"])) if info else []

        class _Cur:
            def fetchall(self):
                return rows
        return _Cur()


def gen_av_view(llm, client: MySQLClient, registry: SkillRegistry, db: str, schema: str, rw: str, name: str,
                ev: str, vindex, embedder=None) -> List[ViewSpec]:
    """MySQL port of realrun._generate_av_view (AV-SQL Algorithm 1): up to T_max attempts. The agent may write one SELECT or a WITH block of several named CTEs, and each named CTE becomes its own view. Each attempt is checked by value retrieval on the block's literals, execution of every CTE, and block/JSON-selection consistency. Every problem and the retrieved values go back to the next attempt. Returns the views (added to `registry`, in dependency order) or []."""
    con = _ColumnsCon(avsql_prepared(client, db).schema_dict)
    feedback = None
    for _ in range(VIEW_VALIDATE_ATTEMPTS):
        cands, selection, raw, block = agents.av_views_selected(llm, schema, rw, name, evidence=ev, dialect="MySQL",
                                                                feedback=feedback, taken=registry.has)
        if not cands:
            if raw is not None:                  # JSON only: the chunk was judged irrelevant
                return []
            feedback = {"cte": None, "selection": None,
                        "error": "no ```sql or ```json block was produced: output both blocks"}
            continue
        problems = contracts.selection_consistency(block, selection, con, dialect="mysql")
        values = (vindex.relevant_values(block, embedder=embedder, tau_edit=0.5, tau_semantic=0.5,
                                         dialect="mysql") if vindex is not None else [])
        errors = []
        for cand in cands:
            registry.add_view(cand)
        for cand in cands:
            ok, msg = validate_view(client, registry, cand, db)
            if not ok:
                errors.append(msg if len(cands) == 1 else f"CTE {cand.description.split(' ')[0]}: {msg}")
        if not errors and not problems:
            return cands
        for cand in reversed(cands):
            registry.remove_view(cand.name)
        feedback = {"cte": block, "selection": raw, "error": "; ".join(errors) or None,
                    "consistency": problems, "values": values}
    return []


def chunk_mysql_tables(client: MySQLClient, db: str) -> List[List[str]]:
    """Tables of each chunk of chunk_mysql_schema, in the same order."""
    if datasets.SCHEMA_PREP == "avsql":
        return [tabs for _text, tabs in avsql_prepared(client, db).chunks()]
    return [re.findall(r'CREATE TABLE\s+`?(\w+)`?', c) for c in chunk_mysql_schema(client, db)]


def chunk_mysql_schema(client: MySQLClient, db: str, budget_chars: int = 12000) -> List[str]:
    """Legacy: pack WHOLE table definitions into chunks of <= budget_chars. Nothing is ever dropped. A table is split only if it alone exceeds the budget, and then the continuation is marked explicitly so the model cannot mistake a fragment for the whole table. Under AV-SQL preprocessing: the compact chunks of avsql_prepared."""
    if db in _CHUNK_CACHE:
        return _CHUNK_CACHE[db]
    if datasets.SCHEMA_PREP == "avsql":
        _CHUNK_CACHE[db] = [text for text, _tabs in avsql_prepared(client, db).chunks()]
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
    """Render ONLY the selected tables, each COMPLETE. Falls back to the first chunk if the selection is empty, so the generator is never handed an empty schema."""
    if datasets.SCHEMA_PREP == "avsql":
        return avsql_prepared(client, db).render(tables) or chunk_mysql_schema(client, db)[0]
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
    """Each split parquet (dw, dw_real, neutron, nova) has: id, db, question, sql (gold), domain_knowledge. `db` is the PHYSICAL database to run against (dw_real -> dw)."""
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
VIEW_SYS = load_prompt("beaver_method/view_sys.txt")
VIEW_USER = load_prompt("beaver_method/view_user.txt")

FINAL_SYS = load_prompt("beaver_method/final_sys.txt")
FINAL_USER = load_prompt("beaver_method/final_user.txt")

DIRECT_SYS = load_prompt("beaver_method/direct_sys.txt")
DIRECT_USER = load_prompt("beaver_method/direct_user.txt")

REVISE_SYS = load_prompt("beaver_method/revise_sys.txt")
REVISE_USER = load_prompt("beaver_method/revise_user.txt")

SEM_SYS = load_prompt("beaver_method/sem_sys.txt")
SEM_USER = load_prompt("beaver_method/sem_user.txt")


def gen_view(llm, schema, req, existing, reforce="") -> Optional[ViewSpec]:
    ex = ""
    if existing:
        ex = EXISTING_VIEWS.format(views="\n".join(
            f"- {v.name} ({v.category}): {v.output_columns}" for v in existing[:6]))
    txt = llm.ask(VIEW_SYS,
                  VIEW_USER.format(schema=schema[:24000], name=req.want_name,
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


def validate_view(client: MySQLClient, registry: SkillRegistry, spec: ViewSpec, db: str) -> Tuple[bool, str]:
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
        # output_columns are stored QUALIFIED (`table.column`) for the reuse guard. The executed result columns are the BARE aliases, so validate on the bare suffix.
        missing = [c for c in spec.output_columns
                   if c.split(".")[-1].strip("`\" ").lower() not in low]
        return (not missing), ("ok" if not missing else f"declared outputs missing: {missing}")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def validate_closure(client: MySQLClient, registry: SkillRegistry, names: List[str],
                     db: str) -> Tuple[bool, Optional[str], str]:
    """Fix #3 — L3 over the FULL DEPENDS_ON closure of `names` (the chosen sub-goal views PLUS every transitive dependency), not just the chosen ones. Each view must execute and expose its declared outputs against the live DB, and each DEPENDS_ON target must still exist. Closes the hole where a view dragged into compose_sql via a dependency edge (e.g. a seed view) reached the final query unchecked. Returns (ok, offending_view_or_None, reason)."""
    # Defensive closure walk (does NOT use registry.topo_closure, which KeyErrors on a dangling edge): a missing DEPENDS_ON target is reported as the offender instead of crashing.
    seen, stack = set(), list(names)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        s = registry.views.get(n)
        if s is None:
            return False, n, f"chosen view {n} not in registry"
        seen.add(n)
        for d in s.depends_on:
            if not registry.has(d):
                return False, n, f"missing dependency {d}"
            stack.append(d)
    # L3: every view in the closure must execute and expose its declared outputs against the live DB.
    for n in seen:
        ok, msg = validate_view(client, registry, registry.views[n], db)
        if not ok:
            return False, n, msg
    return True, None, "ok"


# --------------------------------------------------------------------------- #
# Persistence + seed loading
# --------------------------------------------------------------------------- #
def _save(tag, rows, client, verify, registries=None):
    out = os.path.join(RESULTS_DIR, f"{tag}_beaver.json")
    n = max(1, len(rows))
    json.dump({"verify": verify, "n": len(rows), "n_ok": sum(r["correct"] for r in rows),
               "accuracy": round(sum(r["correct"] for r in rows) / n, 4),
               "reuse": sum(r["reused"] for r in rows), "gen": sum(r["generated"] for r in rows),
               "seed_reuse": sum(r.get("seed_reused", 0) for r in rows),
               "negative_reuse_nontrivial": sum(r.get("negative_reuse", False) for r in rows),
               "mysql_exec_seconds": round(client.exec_seconds, 1), "mysql_n_run": client.n_run,
               "rows": rows, "llm_usage": USAGE.snapshot()}, open(out, "w"), indent=2)
    if registries:
        from dataclasses import asdict
        gdump = {db: {"views": {nm: asdict(v) for nm, v in g.views.items()}, "n_views": g.n_views()}
                 for db, g in registries.items()}
        json.dump(gdump, open(os.path.join(RESULTS_DIR, f"{tag}_beaver_registrys.json"), "w"), indent=2)
    return out


def _init_registry(db: str, seed_dir: str) -> Tuple[SkillRegistry, set]:
    if seed_dir:
        sp = os.path.join(seed_dir, f"{db}.json")
        if os.path.exists(sp):
            g = sqlview.load_registry(sp)
            return g, set(g.views.keys())
    return SkillRegistry(db_id=db), set()


def _retrieval_snapshot(registry: SkillRegistry) -> SkillRegistry:
    """Freeze reusable candidates at question start. Views generated for earlier requests in the current question are valid only through explicit dependencies. They are not historical registry-reuse hits."""
    frozen = SkillRegistry(db_id=registry.db_id)
    for spec in list(registry.views.values()):
        frozen.add_view(spec)
    return frozen


# --------------------------------------------------------------------------- #
# Method loop (identical control flow to sf_method.run)
# --------------------------------------------------------------------------- #
def _filter_runnable_gold(client: MySQLClient, tasks: List[Dict]) -> List[Dict]:
    """Keep only tasks whose GOLD SQL executes on our MariaDB (some BEAVER gold uses MySQL-8-only features — GROUPING(), framed row_number() — that MariaDB rejects). Scoring is only meaningful where gold runs, and this is fair across configs since all share the same gold set."""
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


def run(splits, limit, verify, max_views, model, tag, seed_dir="",
        nxm=False, max_subgoals=8, nx1=False, architecture="legacy", focused_budget=8000,
        use_memory=None):
    # Backward compatibility: historically verify>0 meant both "enable memory" and "run N reuse verifier voters".  Experiments can now enable registry memory independently with verify=0.
    if use_memory is None:
        use_memory = verify > 0
    tasks = load_beaver_tasks(splits, limit)
    client = MySQLClient()
    tasks = _filter_runnable_gold(client, tasks)
    llm = LLM(model=model)
    emb = Embedder()   # used by deterministic (zero-token) reuse selection
    registries: Dict[str, SkillRegistry] = {}
    seed_names: Dict[str, set] = {}
    # Resume: reload rows already computed and skip those tasks (budget-limited providers accumulate across days). {tag}_beaver.json stores {"rows": [...]}.
    rows, _done = [], set()
    _rp = os.path.join(RESULTS_DIR, f"{tag}_beaver.json")
    if os.path.exists(_rp):
        try:
            rows = json.load(open(_rp)).get("rows", [])
            _done = {r["instance_id"] for r in rows}
        except Exception:  # noqa: BLE001
            rows, _done = [], set()
    n_explore_total = 0
    cfg = "S(seed)" if seed_dir else ("A" if use_memory else "B")
    print(f"BEAVER run [{cfg}]: {len(tasks)} tasks | splits={splits} verify={verify} "
          f"memory={int(use_memory)} seed_dir={seed_dir or '-'}\n")
    for ti, t in enumerate(tasks):
        if t["instance_id"] in _done:
            continue
        if ti and ti % 20 == 0:
            _save(tag, rows, client, verify, registries)
        db = t["db"]
        schema = render_mysql_schema(client, db)

        def _mysql_vp(db=db):   # value profile (MySQL): SHOW TABLES + sample each, once per db
            tbls = [list(r)[0] for r in client.run("SHOW TABLES", db).itertuples(index=False)]
            def samp(t):
                d = client.run(f"SELECT * FROM `{t}` LIMIT 500", db)
                return list(d.columns), d.values.tolist()
            return samp, tbls
        schema += valuelink.value_profile_appendix(f"beaver:{db}", _mysql_vp)
        ev = _evidence(t)
        if not use_memory:
            registries[db] = SkillRegistry(db_id=db)              # config B: reset each question
        elif db not in registries:
            registries[db], seed_names[db] = _init_registry(db, seed_dir)
        g = registries.setdefault(db, SkillRegistry(db_id=db))
        sn = seed_names.get(db, set())

        chunks = chunk_mysql_schema(client, db)
        _rw, rw = agents.rewrite_question(llm, "", t["question"], ev)  # schema-free: rewrite into sub-goals needs only the question
        per_tables: Dict[str, set] = {}
        architecture_route = ("nx1" if nx1 else "nxm" if nxm else architecture)
        direct_route = False
        cwt = list(zip(chunks, chunk_mysql_tables(client, db)))
        if architecture == "auto":
            table_index = ", ".join(_table_blocks(client, db).keys())
            reqs, per_tables, adaptive_route, sel_tables, _ncalls = agents.adaptive_requests(
                llm, cwt, rw, table_index,
                render_selected=lambda tabs: filtered_mysql_schema(client, db, tabs),
                estimate_tokens=lambda text: max(1, len(text) // 4),
                focused_budget=focused_budget, max_subgoals=max_subgoals,
                qualify_outputs=True, tag_prefix="bv_")
            direct_route = adaptive_route == "direct_sql"
            architecture_route = (adaptive_route if direct_route else
                                  f"{adaptive_route}_{'registry' if use_memory else 'nomemory'}")
        elif nx1 or architecture == "nx1":
            # N×1 (AV-SQL / SkiewSQL v2m): one whole-question view per schema chunk. NO sub-goal decomposition. Tables per chunk are parsed from its CREATE TABLE statements so each view is generated against its own chunk's schema.
            reqs, per_tables = agents.nx1_requests(cwt, rw)
            sel_tables = set().union(*per_tables.values()) if per_tables else set()
        elif nxm or architecture == "nxm":
            # N×M: decompose the question ONCE with the whole-DB table index in view -> M coherent sub-goals, then align EACH sub-goal against EVERY chunk to gather all its tables (the N×M loop). No arbitrary cap on M (only max_subgoals). A sub-goal whose tables span several chunks still collects all of them.
            table_index = ", ".join(_table_blocks(client, db).keys())
            reqs, per_tables, _ncalls = agents.decompose_and_align(
                llm, chunks, rw, table_index, max_subgoals=max_subgoals, qualify_outputs=True,
                tag_prefix="bv_")
            sel_tables = set().union(*per_tables.values()) if per_tables else set()
        else:
            # Per-chunk proposal: every table in the warehouse is seen by the proposer (nothing is truncated away), and each chunk contributes the tables it judges relevant.
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

        reforce = ""

        chosen, reused, gen, vrej, seed_reused = [], 0, 0, 0, 0
        reused_names, reused_specs = [], []
        resolved_reqs = {}
        retrieval_registry = _retrieval_snapshot(g) if use_memory else g
        for req in reqs:
            spec = None
            if use_memory and sqlview.deterministic_reuse_on():   # Zero-Mem: guard+embedding, no LLM
                spec, _d = sqlview.select_reuse(retrieval_registry, req, emb, tau=0.55)
                if spec is None and _d.get("reason") == "conflicting near-tie":
                    vrej += 1
            elif use_memory and verify > 0:
                cands = sqlview.retrieve_candidates(retrieval_registry, req, embedder=None, k=6)
                if cands:
                    picks = [agents.choose_reuse(llm, req, cands) for _ in range(verify)]
                    names = [p[0] for p in picks if p[0]]
                    if names:
                        top, cnt = Counter(names).most_common(1)[0]
                        if cnt * 2 > verify:
                            spec = next(c for c in cands if c.name == top)
                    if spec is None:
                        vrej += 1
            elif use_memory:
                # Registry reuse without an LLM verifier, matching realrun.py's default memory arm.
                spec, _d = sqlview.retrieve(retrieval_registry, req, emb, tau=0.55)
            if spec is not None:
                chosen.append(spec); reused += 1
                reused_names.append(spec.name); reused_specs.append(spec)
                resolved_reqs[req.want_name] = spec
                if spec.name in sn:
                    seed_reused += 1
                continue
            # PER-SUB-GOAL COLUMN EXPLORATION: probe the columns THIS sub-goal needs, and give the evidence to the view generator — the step that actually chooses columns. (Injecting it only at compose time was too late: the views were already written from DDL names.) In N×M mode each sub-goal generates against ONLY its aligned tables (max-recall focus). otherwise against the shared union schema.
            req_schema = (filtered_mysql_schema(client, db, per_tables[req.want_name])
                          if per_tables.get(req.want_name) else schema)
            sub_rf = reforce
            declared = [resolved_reqs[n] for n in req.depends_on if n in resolved_reqs]
            missing_deps = [n for n in req.depends_on if n not in resolved_reqs]
            if missing_deps and not req.may_read_base_tables:
                continue
            if (nx1 or req.holistic) and datasets.SCHEMA_PREP == "avsql":
                cands = gen_av_view(llm, client, g, db, req_schema, rw, req.want_name, ev,
                                    mysql_value_index(client, db), embedder=emb)
                if cands:                            # already validated and in the registry
                    chosen.extend(cands); gen += len(cands); resolved_reqs[req.want_name] = cands[-1]
                continue
            if nx1 or req.holistic:
                cand = agents.av_view(llm, req_schema, rw, req.want_name, evidence=ev, dialect="MySQL")
            else:
                offered = declared if req.depends_on else list(g.views.values())
                cand = gen_view(llm, req_schema, req, offered, reforce=sub_rf)
            if cand is None:
                continue
            if req.depends_on and not req.may_read_base_tables:
                cand.depends_on = list(dict.fromkeys(cand.depends_on + [v.name for v in declared]))
            if g.has(cand.name):
                cand.name = f"{cand.name}_{len(g.views)}"
            g.add_view(cand)
            ok, _vmsg = validate_view(client, g, cand, db)
            if ok:
                chosen.append(cand); gen += 1; resolved_reqs[req.want_name] = cand
            else:
                g.remove_view(cand.name)

        # Fix #3 — guard the dependency closure: drop any chosen view whose closure (itself or a dep pulled in via DEPENDS_ON) fails L3 against the live DB, before it reaches compose_sql.
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

        # semantic revisor (conservative single pass. Accept only if it still executes)
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
                     "generated": gen, "verify_reject": vrej, "registry_views": g.n_views(),
                     "architecture_route": architecture_route,
                     "seed_views": len(sn), "used_reuse": reused > 0,
                     "negative_reuse": bool(used_nontrivial and not correct_b),
                     "error": err or serr, "question": t["question"], "pred_sql": composed})
        print(f"  {t['instance_id']:14} {db[:10]:10} ok={int(correct_b)} reuse={reused}"
              f"(seed={seed_reused}) gen={gen} vrej={vrej} route={architecture_route} registry={g.n_views()} "
              f"{('' if correct_b else (err or serr)[:40])}", flush=True)
        _done.add(t["instance_id"])
        _save(tag, rows, client, verify, registries)   # persist every question so a budget-stop can resume

    n_ok = sum(r["correct"] for r in rows)
    print(f"\n=== BEAVER summary [{cfg}] === tasks {len(rows)} | correct {n_ok} "
          f"({100*n_ok/max(1,len(rows)):.1f}%) | reuse {sum(r['reused'] for r in rows)} "
          f"(seed {sum(r['seed_reused'] for r in rows)}) | gen {sum(r['generated'] for r in rows)} | "
          f"neg-reuse {sum(r['negative_reuse'] for r in rows)}")
    out = _save(tag, rows, client, verify, registries)
    print(f"  wrote {out}")
    client.close()


def main():
    ap = argparse.ArgumentParser(description="Run SkiewSQL (A/B/S) on the BEAVER benchmark (MySQL).")
    ap.add_argument("--splits", default="neutron", help="comma list of query splits: dw,dw_real,neutron,nova")
    ap.add_argument("--limit", type=int, default=25, help="max questions per split")
    ap.add_argument("--verify", type=int, default=3,
                    help="reuse-selector voters (reject-biased strict majority). 0 = config B (no reuse)")
    ap.add_argument("--max_views", type=int, default=3)
    ap.add_argument("--architecture", default="legacy",
                    choices=["legacy", "auto", "nx1", "nxm"])
    ap.add_argument("--memory", type=int, choices=[0, 1], default=None,
                    help="registry memory independently of --verify (default: on iff verify>0)")
    ap.add_argument("--focused_budget", type=int, default=8000,
                    help="deprecated compatibility knob. Auto now routes by semantic difficulty")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="beaver")
    ap.add_argument("--seed_dir", default="", help="config S: dir of frozen seed registries ({db}.json)")
    ap.add_argument("--nxm", type=int, default=0,
                    help="1 = N×M decomposition: decompose the question once (whole-DB table index), then align each of M sub-goals against all N chunks (no cap at max_views)")
    ap.add_argument("--nx1", type=int, default=0,
                    help="1 = N×1 (AV-SQL / SkiewSQL v2m): one whole-question view per chunk, no sub-goal decomposition. Overrides --nxm.")
    ap.add_argument("--max_subgoals", type=int, default=4, help="N×M mode: cap on M sub-goals")
    args = ap.parse_args()
    if args.nx1:
        args.architecture = "nx1"
    elif args.nxm:
        args.architecture = "nxm"
    splits = [s.strip() for s in args.splits.split(",") if s.strip()]
    try:
        run(splits, args.limit, args.verify, args.max_views, args.model, args.tag, seed_dir=args.seed_dir,
            nxm=bool(args.nxm), max_subgoals=args.max_subgoals,
            nx1=bool(args.nx1), architecture=args.architecture,
            focused_budget=args.focused_budget, use_memory=(None if args.memory is None else bool(args.memory)))
    except DailyBudgetExhausted:
        print("[budget] daily request budget spent — progress saved. Resume next run", flush=True)
        sys.exit(3)                                    # non-zero: orchestrator leaves stage unmarked


if __name__ == "__main__":
    main()
