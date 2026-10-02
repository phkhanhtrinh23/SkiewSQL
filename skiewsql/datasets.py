"""datasets.py — real Spider / BIRD loaders, schema rendering, SQLite execution, and Spider-style execution-accuracy comparison. Nothing here calls an LLM. It provides the grounded `D` (database) the agents and the view graph execute against, plus the gold-vs-prediction result-set comparison used as the Execution Accuracy (EX) metric."""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from func_timeout import func_timeout, FunctionTimedOut

SPIDER_ROOT = "/mnt/win_d/data/sft_data_collections/spider"
BIRD_DEV_ROOT = "/mnt/win_d/data/sft_data_collections/bird/dev"
SQLFLOW_ROOT = "/mnt/win_d/skill_driven_agent_view/datasets"   # SQLFlow augmented JSONs live here


# --------------------------------------------------------------------------- #
# Question records
# --------------------------------------------------------------------------- #
@dataclass
class Question:
    qid: str
    db_id: str
    question: str
    gold_sql: str
    evidence: str = ""          # BIRD external knowledge
    dataset: str = "spider"
    extra: Dict = field(default_factory=dict)


def load_spider(split: str = "dev") -> Tuple[List[Question], Dict[str, str], str]:
    """Return (questions, tables_by_db_json_path?, db_root). Uses dev.json + database/."""
    path = os.path.join(SPIDER_ROOT, f"{split}.json")
    data = json.load(open(path))
    qs = []
    for i, d in enumerate(data):
        qs.append(Question(qid=f"spider_{split}_{i}", db_id=d["db_id"],
                           question=d["question"], gold_sql=d["query"], dataset="spider"))
    db_root = os.path.join(SPIDER_ROOT, "database")
    return qs, os.path.join(SPIDER_ROOT, "tables.json"), db_root


SPIDER_FUSION_ROOT = "/mnt/win_d/data_FusionSQL/spider"
BIRD_FUSION_ROOT = "/mnt/win_d/data_FusionSQL/bird"


def load_spider_fusion() -> Tuple[List[Question], Optional[str], str]:
    """Spider dev, FusionSQL copy: sft_spider_dev_text2sql.json (fields question/sql/db_id/evidence), SQLite at database/<db_id>/<db_id>.sqlite."""
    path = os.path.join(SPIDER_FUSION_ROOT, "sft_spider_dev_text2sql.json")
    data = json.load(open(path))
    qs = []
    for i, d in enumerate(data):
        qs.append(Question(qid=f"spider_{i}", db_id=d["db_id"],
                           question=d.get("question") or d.get("text", ""),
                           gold_sql=d["sql"], evidence=str(d.get("evidence", "") or ""),
                           dataset="spider"))
    return qs, None, os.path.join(SPIDER_FUSION_ROOT, "database")


def load_bird_fusion() -> Tuple[List[Question], Optional[str], str]:
    """BIRD dev, FusionSQL copy: sft_bird_dev_text2sql.json, SQLite at dev/dev_databases/<db_id>/<db_id>.sqlite. (Requires `git lfs pull` in the repo first.)"""
    path = os.path.join(BIRD_FUSION_ROOT, "sft_bird_dev_text2sql.json")
    data = json.load(open(path))
    qs = []
    for i, d in enumerate(data):
        qs.append(Question(qid=f"bird_{i}", db_id=d["db_id"],
                           question=d.get("question") or d.get("text", ""),
                           gold_sql=d.get("sql") or d.get("SQL", ""),
                           evidence=str(d.get("evidence", "") or ""), dataset="bird"))
    return qs, None, os.path.join(BIRD_FUSION_ROOT, "dev", "dev_databases")


def load_bird(split: str = "dev") -> Tuple[List[Question], str, str]:
    path = os.path.join(BIRD_DEV_ROOT, "dev.json")
    data = json.load(open(path))
    qs = []
    for i, d in enumerate(data):
        qs.append(Question(
            qid=f"bird_{split}_{d.get('question_id', i)}", db_id=d["db_id"],
            question=d["question"], gold_sql=d["SQL"], evidence=str(d.get("evidence", "")),
            dataset="bird"))
    db_root = os.path.join(BIRD_DEV_ROOT, "dev_databases")
    return qs, os.path.join(BIRD_DEV_ROOT, "dev_tables.json"), db_root


def load_bird_minidev() -> Tuple[List[Question], str, str]:
    """BIRD Mini-Dev (birdsql/bird_mini_dev): a curated 500-question subset over the SAME 11 BIRD dev databases. Standard BIRD record format (db_id/question/evidence/SQL/difficulty)."""
    path = os.path.join(BIRD_DEV_ROOT, "mini_dev_sqlite.json")
    data = json.load(open(path))
    qs = []
    for i, d in enumerate(data):
        qs.append(Question(
            qid=f"birdmini_{d.get('question_id', i)}", db_id=d["db_id"],
            question=d["question"], gold_sql=d["SQL"], evidence=str(d.get("evidence", "")),
            dataset="bird", extra={"difficulty": d.get("difficulty", "")}))
    db_root = os.path.join(BIRD_DEV_ROOT, "dev_databases")
    return qs, os.path.join(BIRD_DEV_ROOT, "dev_tables.json"), db_root


def load_sqlflow(variant: str = "spider") -> Tuple[List[Question], Optional[str], str]:
    """SQLFlow (debugger123/SQLFlow) augmented Text-to-SQL. Each example is (db_id, SQL, question, evidence, ...) over the ORIGINAL Spider/BIRD databases. We score its augmented SQL as gold. Returns (questions, tables_path=None, db_root)."""
    path = os.path.join(SQLFLOW_ROOT, f"sqlflow_{variant}.json")
    data = json.load(open(path))
    if variant == "spider":
        db_root = os.path.join(SPIDER_ROOT, "database")
    elif variant == "bird":                       # SQLFlow-bird is augmented from BIRD-*train*
        db_root = "/mnt/win_d/data/sft_data_collections/bird/train/train_databases"
    else:                                          # ehrsql (mimic_iii/eicu) — DBs must exist on disk
        db_root = os.path.join(SQLFLOW_ROOT, f"{variant}_databases")
    qs = []
    for i, d in enumerate(data):
        qs.append(Question(
            qid=f"sqlflow_{variant}_{i}", db_id=d["db_id"], question=d["question"],
            gold_sql=d["SQL"], evidence=str(d.get("evidence", "")), dataset=f"sqlflow_{variant}",
            extra={"variation": d.get("sql_variation_type", "")}))
    return qs, None, db_root


def db_path(db_root: str, db_id: str, dataset: str) -> str:
    if dataset == "bird":
        return os.path.join(db_root, db_id, f"{db_id}.sqlite")
    return os.path.join(db_root, db_id, f"{db_id}.sqlite")


# --------------------------------------------------------------------------- #
# Schema rendering (compact, with sample rows + FKs) — the agents' view of D
# --------------------------------------------------------------------------- #
def _columns(con: sqlite3.Connection, table: str):
    return con.execute(f'PRAGMA table_info("{table}")').fetchall()


def _foreign_keys(con: sqlite3.Connection, table: str):
    return con.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()


def list_tables(con: sqlite3.Connection) -> List[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [r[0] for r in rows]


def table_block(con: sqlite3.Connection, t: str, sample_rows: int = 2) -> str:
    """A compact CREATE-like rendering of one table (types + sample values + FKs)."""
    cols = _columns(con, t)
    col_lines = []
    try:
        sample = con.execute(f'SELECT * FROM "{t}" LIMIT {sample_rows}').fetchall()
    except Exception:  # noqa: BLE001
        sample = []
    colnames = [c[1] for c in cols]
    for c in cols:
        cid, name, ctype, notnull, dflt, pk = c
        tag = " PRIMARY KEY" if pk else ""
        examples = []
        idx = colnames.index(name)
        for row in sample:
            if idx < len(row) and row[idx] is not None:
                v = str(row[idx])
                if len(v) > 24:
                    v = v[:24] + "…"
                examples.append(v)
        ex = f"  -- e.g. {', '.join(examples[:2])}" if examples else ""
        col_lines.append(f'    "{name}" {ctype or "TEXT"}{tag}{ex}')
    fks = _foreign_keys(con, t)
    fk_lines = [f'    FOREIGN KEY ("{fk[3]}") REFERENCES "{fk[2]}"("{fk[4]}")' for fk in fks]
    body = ",\n".join(col_lines + fk_lines)
    return f'CREATE TABLE "{t}" (\n{body}\n);'


def render_schema(con: sqlite3.Connection, sample_rows: int = 2, max_tables: int = 60) -> str:
    """Whole-schema compact rendering (all tables)."""
    return "\n\n".join(table_block(con, t, sample_rows) for t in list_tables(con)[:max_tables])


# --------------------------------------------------------------------------- #
# AV-SQL Stage-2 schema handling: compression (~10x near-dup clustering) + length-based chunking under a token budget B.
# --------------------------------------------------------------------------- #
import re as _re

try:
    import tiktoken as _tk
    _ENC = _tk.get_encoding("cl100k_base")

    def est_tokens(text: str) -> int:
        return len(_ENC.encode(text))
except Exception:  # noqa: BLE001
    def est_tokens(text: str) -> int:
        return max(1, len(text) // 4)


def _stem(name: str) -> str:
    """Strip trailing years / numeric suffixes so near-duplicate tables cluster (e.g. ga_sessions_20170101, year_2003 -> ga_sessions_<N>, year_<N>)."""
    s = _re.sub(r"(19|20)\d{2}", "<YYYY>", name)
    s = _re.sub(r"\d+$", "<N>", s)
    s = _re.sub(r"_\d+_", "_<N>_", s)
    return s


def compress_schema(con: sqlite3.Connection, sample_rows: int = 2):
    """Cluster near-duplicate tables by name stem. Render one representative per cluster with a note listing the collapsed siblings (AV-SQL §4.1.1). Returns (text, clusters)."""
    tables = list_tables(con)
    clusters: Dict[str, List[str]] = {}
    for t in tables:
        clusters.setdefault(_stem(t), []).append(t)
    blocks, info = [], {}
    for stem, members in clusters.items():
        blk = table_block(con, members[0], sample_rows)
        if len(members) > 1:
            others = ", ".join(members[1:8]) + (" …" if len(members) > 9 else "")
            blk += f"\n-- (+{len(members)-1} near-duplicate tables sharing this schema: {others})"
        blocks.append(blk)
        info[stem] = members
    return "\n\n".join(blocks), info


def chunk_schema(con: sqlite3.Connection, budget_tokens: int = 8000,
                 compress: bool = True, sample_rows: int = 2):
    """Length-based partition: pack whole (optionally compressed) table blocks into chunks whose estimated token length stays < budget_tokens (AV-SQL §4.1.2). Returns a list of (chunk_text, [tables_in_chunk])."""
    tables = list_tables(con)
    if compress:
        seen, reps = set(), []
        for t in tables:
            st = _stem(t)
            if st in seen:
                continue
            seen.add(st)
            reps.append(t)
        tables = reps
    blocks = [(t, table_block(con, t, sample_rows)) for t in tables]
    chunks, cur, cur_tabs, cur_tok = [], [], [], 0
    for t, blk in blocks:
        bt = est_tokens(blk)
        if cur and cur_tok + bt > budget_tokens:
            chunks.append(("\n\n".join(cur), cur_tabs))
            cur, cur_tabs, cur_tok = [], [], 0
        cur.append(blk)
        cur_tabs.append(t)
        cur_tok += bt
    if cur:
        chunks.append(("\n\n".join(cur), cur_tabs))
    return chunks


# --------------------------------------------------------------------------- #
# Execution + Spider-style EX comparison
# --------------------------------------------------------------------------- #
class ExecError(Exception):
    pass


# A pred that returns more than this can't match a small gold answer anyway. Cap the fetch so a runaway query (e.g. an accidental cross join) can't materialize millions of rows and hang.
MAX_RESULT_ROWS = 100000


def connect(path: str) -> sqlite3.Connection:
    # check_same_thread=False: func_timeout runs queries in a worker thread.
    con = sqlite3.connect(path, check_same_thread=False)
    con.text_factory = lambda b: b.decode("utf-8", "ignore")
    return con


def run_sql(con: sqlite3.Connection, sql: str, timeout: float = 30.0):
    """Execute in the MAIN thread with a SQLite progress handler as the timeout. This replaces func_timeout, whose thread-killing (PyThreadState_SetAsyncExc) corrupts SQLite's C state on aborted queries and segfaults — a real crash we hit on Spider2's slow queries."""
    import time
    deadline = time.time() + timeout
    con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 20000)
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(MAX_RESULT_ROWS + 1)
        if len(rows) > MAX_RESULT_ROWS:
            raise ExecError(f"result too large (>{MAX_RESULT_ROWS} rows)")
        return rows
    except sqlite3.OperationalError as e:
        raise ExecError("timeout" if time.time() > deadline else f"OperationalError: {e}")
    except Exception as e:  # noqa: BLE001
        raise ExecError(f"{type(e).__name__}: {e}")
    finally:
        con.set_progress_handler(None, 0)


def _norm_rows(rows, order_sensitive: bool):
    """Normalize for set comparison (Spider style): round floats, multiset of rows, order-agnostic columns within a row (Spider EX ignores column order)."""
    def norm_val(x):
        if isinstance(x, float):
            return round(x, 2)
        return x

    out = []
    for row in rows:
        vals = tuple(sorted((str(norm_val(x)) for x in row)))
        out.append(vals)
    if not order_sensitive:
        out = sorted(out)
    return out


def gold_is_ordered(gold_sql: str) -> bool:
    g = gold_sql.lower()
    return " order by " in g


def ex_match(con: sqlite3.Connection, pred_sql: str, gold_sql: str,
             timeout: float = 30.0) -> Tuple[bool, Optional[str]]:
    """Execution accuracy: True if predicted result set matches gold result set. Returns (match, error_message_if_pred_failed)."""
    try:
        gold_rows = run_sql(con, gold_sql, timeout)
    except ExecError as e:
        # gold itself failed (rare data issue) — cannot score
        return False, f"GOLD_FAILED: {e}"
    try:
        pred_rows = run_sql(con, pred_sql, timeout)
    except ExecError as e:
        return False, str(e)
    order = gold_is_ordered(gold_sql)
    return _norm_rows(pred_rows, order) == _norm_rows(gold_rows, order), None
