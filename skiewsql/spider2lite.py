"""spider2lite.py — loader + execution-accuracy scorer for the *local-SQLite* subset of Spider 2.0-lite (the `local*` instances), so SkiewSQL can be evaluated on Spider2's much harder, analytics-style questions with the existing SQLite pipeline. Spider2-lite scores a prediction by running it and comparing the RESULT TABLE to a gold result CSV (not gold SQL): for every gold column there must be a predicted column whose values match, with a 1e-2 float tolerance, optional per-column-subset (`condition_cols`) and order-insensitivity (`ignore_order`), and multiple acceptable gold variants (a/b/…). `compare_pandas_table` / `compare_multi_pandas_table` below are copied VERBATIM from the official `spider2-lite/evaluation_suite/evaluate_utils.py` so our scoring matches theirs (we can't import that module: it does `from google.cloud import bigquery` at top level).

Only the `local*` tasks run here — the `bq*` / `sf*` tasks need BigQuery/Snowflake and are out of scope. Data lives in the local Spider2 checkout: questions : Spider2/spider2-lite/spider2-lite.jsonl        (instance_id, db, question, external_knowledge) eval spec : .../evaluation_suite/gold/spider2lite_eval.jsonl (condition_cols, ignore_order) gold csv  : .../evaluation_suite/gold/exec_result/<iid>[_x].csv databases : Spider2/output/sqlite/<db>/<db>.sqlite"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sqlite3
from typing import List, Optional, Tuple

import pandas as pd
from func_timeout import func_timeout, FunctionTimedOut

from skiewsql.datasets import Question, ExecError, MAX_RESULT_ROWS

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPIDER2_ROOT = os.environ.get("SPIDER2_ROOT", os.path.join(_PROJECT_ROOT, "data", "spider2"))
LITE_ROOT = os.path.join(SPIDER2_ROOT, "spider2-lite")
SQLITE_ROOT = os.path.join(SPIDER2_ROOT, "output", "sqlite")
QUESTIONS = os.path.join(LITE_ROOT, "spider2-lite.jsonl")
EVAL_SPEC = os.path.join(LITE_ROOT, "evaluation_suite", "gold", "spider2lite_eval.jsonl")
GOLD_SQL_DIR = os.path.join(LITE_ROOT, "evaluation_suite", "gold", "sql")
GOLD_CSV_DIR = os.path.join(LITE_ROOT, "evaluation_suite", "gold", "exec_result")
DOCS_DIR = os.path.join(LITE_ROOT, "resource", "documents")


# --------------------------------------------------------------------------- #
# Official Spider2 comparison (copied verbatim. Pandas + math only)
# --------------------------------------------------------------------------- #
def compare_pandas_table(pred, gold, condition_cols=[], ignore_order=False):
    tolerance = 1e-2

    def vectors_match(v1, v2, tol=tolerance, ignore_order_=False):
        if ignore_order_:
            v1, v2 = (sorted(v1, key=lambda x: (x is None, str(x), isinstance(x, (int, float)))),
                      sorted(v2, key=lambda x: (x is None, str(x), isinstance(x, (int, float)))))
        if len(v1) != len(v2):
            return False
        for a, b in zip(v1, v2):
            if pd.isna(a) and pd.isna(b):
                continue
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                if not math.isclose(float(a), float(b), abs_tol=tol):
                    return False
            elif a != b:
                return False
        return True

    if condition_cols != []:
        gold_cols = gold.iloc[:, condition_cols]
    else:
        gold_cols = gold
    pred_cols = pred
    t_gold_list = gold_cols.transpose().values.tolist()
    t_pred_list = pred_cols.transpose().values.tolist()
    score = 1
    for _, gold_v in enumerate(t_gold_list):
        if not any(vectors_match(gold_v, pred_v, ignore_order_=ignore_order) for pred_v in t_pred_list):
            score = 0
        else:
            for j, pred_v in enumerate(t_pred_list):
                if vectors_match(gold_v, pred_v, ignore_order_=ignore_order):
                    break
    return score


def compare_multi_pandas_table(pred, multi_gold, multi_condition_cols=[], multi_ignore_order=False):
    if multi_condition_cols in ([], [[]], [None], None):
        multi_condition_cols = [[] for _ in range(len(multi_gold))]
    elif len(multi_gold) > 1 and not all(isinstance(sublist, list) for sublist in multi_condition_cols):
        multi_condition_cols = [multi_condition_cols for _ in range(len(multi_gold))]
    multi_ignore_order = [multi_ignore_order for _ in range(len(multi_gold))]
    for i, gold in enumerate(multi_gold):
        if compare_pandas_table(pred, gold, multi_condition_cols[i], multi_ignore_order[i]):
            return 1
    return 0


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _eval_spec() -> dict:
    spec = {}
    for line in open(EVAL_SPEC):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        spec[r["instance_id"]] = {"condition_cols": r.get("condition_cols", []),
                                  "ignore_order": bool(r.get("ignore_order", False))}
    return spec


def _gold_csvs(iid: str) -> List[str]:
    """All acceptable gold result CSVs for an instance: <iid>.csv or <iid>_a.csv/_b.csv/…"""
    exact = os.path.join(GOLD_CSV_DIR, f"{iid}.csv")
    if os.path.exists(exact):
        return [exact]
    return sorted(glob.glob(os.path.join(GOLD_CSV_DIR, f"{iid}_*.csv")))


def db_path(db_id: str) -> str:
    return os.path.join(SQLITE_ROOT, db_id, f"{db_id}.sqlite")


def _evidence(rec: dict) -> str:
    ek = rec.get("external_knowledge")
    if not ek:
        return ""
    p = os.path.join(DOCS_DIR, ek)
    if os.path.exists(p):
        try:
            # Spider2 knowledge docs are huge and get injected into every stage. Cap tightly.
            return open(p, encoding="utf-8", errors="ignore").read()[:1200]
        except Exception:  # noqa: BLE001
            return ""
    return ""


def load_local(require_gold_csv: bool = True) -> Tuple[List[Question], str]:
    """Return (questions, db_root) for the runnable local-SQLite Spider2-lite subset. Only instances whose SQLite DB exists and (by default) that have a gold result CSV."""
    spec = _eval_spec()
    qs: List[Question] = []
    for line in open(QUESTIONS):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        iid, db = rec["instance_id"], rec["db"]
        if not iid.startswith("local"):
            continue
        if not os.path.exists(db_path(db)):
            continue
        golds = _gold_csvs(iid)
        if require_gold_csv and not golds:
            continue
        gsql_path = os.path.join(GOLD_SQL_DIR, f"{iid}.sql")
        gold_sql = open(gsql_path).read() if os.path.exists(gsql_path) else ""
        s = spec.get(iid, {"condition_cols": [], "ignore_order": True})
        qs.append(Question(
            qid=iid, db_id=db, question=rec["question"], gold_sql=gold_sql,
            evidence=_evidence(rec), dataset="spider2lite",
            extra={"gold_csvs": golds, "condition_cols": s["condition_cols"],
                   "ignore_order": s["ignore_order"]}))
    return qs, SQLITE_ROOT


# --------------------------------------------------------------------------- #
# Scoring (execution accuracy against gold result CSV)
# --------------------------------------------------------------------------- #
def _run_df(con: sqlite3.Connection, sql: str, timeout: float = 60.0) -> pd.DataFrame:
    """Main-thread execution with a SQLite progress-handler timeout (no func_timeout thread killing, which segfaults on aborted queries)."""
    import time
    deadline = time.time() + timeout
    con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 20000)
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(MAX_RESULT_ROWS + 1)          # capped fetch: no giant DataFrame
        if len(rows) > MAX_RESULT_ROWS:
            raise ExecError(f"result too large (>{MAX_RESULT_ROWS} rows)")
        cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame(rows, columns=cols)
    except ExecError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ExecError("timeout" if time.time() > deadline else f"{type(e).__name__}: {e}")
    finally:
        con.set_progress_handler(None, 0)


def score(con: sqlite3.Connection, pred_sql: str, q: Question) -> Tuple[bool, Optional[str]]:
    """Execution accuracy: run pred on the SQLite DB, compare its result table to the gold CSV(s) with Spider2's official column-subset comparison. Returns (correct, error)."""
    golds = q.extra.get("gold_csvs", [])
    if not golds:
        return False, "no gold csv"
    try:
        pred_df = _run_df(con, pred_sql)
    except ExecError as e:
        return False, str(e)
    if pred_df is None or pred_df.shape[1] == 0:
        return False, "empty prediction"
    try:
        multi_gold = [pd.read_csv(g) for g in golds]
    except Exception as e:  # noqa: BLE001
        return False, f"gold-csv read failed: {e}"
    cc = q.extra.get("condition_cols", [])
    io = q.extra.get("ignore_order", True)
    try:
        # match official evaluate.py: single gold -> compare_pandas_table (condition_cols applied as-is). Multiple gold variants -> compare_multi (broadcasts them).
        if len(multi_gold) == 1:
            ok = compare_pandas_table(pred_df, multi_gold[0], cc, io)
        else:
            ok = compare_multi_pandas_table(pred_df, multi_gold, cc, io)
    except Exception as e:  # noqa: BLE001
        return False, f"compare failed: {e}"
    return bool(ok), None


# --------------------------------------------------------------------------- #
# quick manual check
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import collections
    qs, root = load_local()
    by = collections.Counter(q.db_id for q in qs)
    print(f"Spider2-lite local runnable: {len(qs)} questions across {len(by)} DBs")
    for db, n in by.most_common(12):
        print(f"  {db:28} {n}")
