"""
spider2bq.py — BigQuery execution backend + a COST-GUARDED probe for the Spider 2.0-lite `bq*`
tasks (the large, cloud-only, nested/date-sharded BigQuery schemas).

This is deliberately a small, self-contained probe (not the full A/B/S view-memory pipeline):
generate BigQuery Standard SQL from the schema DDL → execute on BigQuery with a hard cost guard
→ score against the gold result CSV. Its purpose is to (a) prove the BigQuery backend works and
(b) MEASURE the real $ cost per task before committing to the full 180-task / view-memory run.

Cost safety:
  * every query is DRY-RUN first; if it would scan > MAX_SCAN_GB it is SKIPPED (not executed);
  * real `total_bytes_billed` is summed and converted to USD at the on-demand rate;
  * query cache is disabled so cost numbers are worst-case (a real run may be cheaper).

Reuses the schema-compression idea (collapse date-sharded tables) and the official Spider2
result comparison from spider2lite.py.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig

from skiewsql.llm import LLM, extract_code
from skiewsql.spider2lite import (compare_multi_pandas_table, _eval_spec, _gold_csvs,
                                  QUESTIONS, DOCS_DIR)

SP2 = "/mnt/win_d/Multilingual_Text_to_SQL_code_backend/Spider2/spider2-lite"
BQ_ROOT = os.path.join(SP2, "resource", "databases", "bigquery")
CRED = os.path.join(SP2, "evaluation_suite", "bigquery_credential.json")

PRICE_PER_TB = 6.25          # BigQuery on-demand USD / TB scanned
MAX_SCAN_GB = 5.0            # cost guard: never execute a query that would scan more than this


# --------------------------------------------------------------------------- #
# BigQuery client with dry-run cost guard + billing accounting
# --------------------------------------------------------------------------- #
class BQClient:
    def __init__(self, cred: str = CRED, max_gb: float = MAX_SCAN_GB):
        self.c = bigquery.Client.from_service_account_json(cred)
        self.max_gb = max_gb
        self.bytes_billed = 0
        self.bytes_dryrun = 0
        self.n_run = 0
        self.n_skipped_cost = 0

    def dry_gb(self, sql: str) -> float:
        j = self.c.query(sql, job_config=QueryJobConfig(dry_run=True, use_query_cache=False))
        return (j.total_bytes_processed or 0) / 1e9

    def dry(self, sql: str) -> Tuple[bool, str, List[str], float]:
        """FREE validation: returns (valid, error, result_columns, est_GB). Scans 0 bytes."""
        try:
            j = self.c.query(sql, job_config=QueryJobConfig(dry_run=True, use_query_cache=False))
            cols = [f.name for f in (j.schema or [])]
            return True, "", cols, (j.total_bytes_processed or 0) / 1e9
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {str(e)[:200]}", [], 0.0

    def run(self, sql: str, cap_rows: int = 100000, sleep_s: float = 0.0) -> pd.DataFrame:
        gb = self.dry_gb(sql)                        # raises on invalid SQL (caught by caller)
        self.bytes_dryrun += int(gb * 1e9)
        if gb > self.max_gb:
            self.n_skipped_cost += 1
            raise RuntimeError(f"cost-guard: would scan {gb:.2f} GB > {self.max_gb} GB")
        job = self.c.query(sql, job_config=QueryJobConfig(use_query_cache=False))
        it = job.result(max_results=cap_rows)
        cols = [f.name for f in it.schema]
        rows = [list(r.values()) for r in it]
        self.bytes_billed += (job.total_bytes_billed or 0)
        self.n_run += 1
        if sleep_s:
            import time
            time.sleep(sleep_s)                      # be gentle on quota / rate limits
        return pd.DataFrame(rows, columns=cols)

    @property
    def cost_usd(self) -> float:
        return self.bytes_billed / 1e12 * PRICE_PER_TB


# --------------------------------------------------------------------------- #
# Schema rendering (collapse date/number-sharded tables → one representative)
# --------------------------------------------------------------------------- #
def _stem(name: str) -> str:
    s = re.sub(r"(19|20)\d{6}$", "<YYYYMMDD>", name)
    s = re.sub(r"(19|20)\d{4}$", "<YYYYMM>", s)
    s = re.sub(r"\d+$", "<N>", s)
    return s


def render_bq_schema(db: str, max_chars: int = 16000) -> str:
    """Concatenate the CREATE TABLE DDLs for a bq database, collapsing sharded tables."""
    ddls: List[Tuple[str, str]] = []
    for ddlcsv in glob.glob(os.path.join(BQ_ROOT, db, "**", "DDL.csv"), recursive=True):
        try:
            for row in csv.DictReader(open(ddlcsv)):
                if row.get("ddl"):
                    ddls.append((row.get("table_name", ""), row["ddl"]))
        except Exception:  # noqa: BLE001
            continue
    seen: Dict[str, int] = {}
    blocks: List[str] = []
    for name, ddl in ddls:
        st = _stem(name)
        if st in seen:
            seen[st] += 1
            continue
        seen[st] = 1
        blocks.append(ddl)
    text = "\n\n".join(blocks)
    shards = [f"{st} (+{n - 1} sharded siblings)" for st, n in seen.items() if n > 1]
    if shards:
        text += "\n\n-- date/number-sharded table groups: " + "; ".join(shards[:10])
    return text[:max_chars]


def _evidence(rec: dict) -> str:
    ek = rec.get("external_knowledge")
    if ek and os.path.exists(os.path.join(DOCS_DIR, ek)):
        try:
            return "External knowledge:\n" + open(os.path.join(DOCS_DIR, ek),
                                                   encoding="utf-8", errors="ignore").read()[:2000]
        except Exception:  # noqa: BLE001
            return ""
    return ""


# --------------------------------------------------------------------------- #
# BigQuery SQL generation (dialect-aware)
# --------------------------------------------------------------------------- #
GEN_SYS = (
    "You are a BigQuery Standard SQL generator. Given the schema (BigQuery DDL) and a question, "
    "write ONE executable BigQuery query. Use backtick-quoted fully-qualified table names exactly "
    "as in the DDL (`project.dataset.table`). Handle nested/repeated fields with UNNEST, and "
    "date-sharded tables with wildcard tables + _TABLE_SUFFIX when appropriate. Output one ```sql "
    "block only, no explanation."
)
GEN_USER = """BigQuery schema (DDL):
{schema}

Question: {question}
{evidence}
{error}
```sql
SELECT ...
```"""


def gen_bq_sql(llm: LLM, schema: str, question: str, evidence: str,
               prior_error: Optional[str] = None) -> Optional[str]:
    err = f"\nThe previous query failed with:\n{prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(GEN_SYS, GEN_USER.format(schema=schema, question=question, evidence=evidence,
                                           error=err), tag="bq_gen", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


# --------------------------------------------------------------------------- #
# Load bq tasks (only those with a gold CSV, so they are scorable)
# --------------------------------------------------------------------------- #
def load_bq_tasks(limit: int, dbs: Optional[List[str]] = None) -> List[dict]:
    spec = _eval_spec()
    out = []
    for line in open(QUESTIONS):
        line = line.strip()
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        iid = r["instance_id"]
        if not iid.startswith("bq"):
            continue
        if dbs and r["db"] not in dbs:
            continue
        golds = _gold_csvs(iid)
        if not golds:
            continue
        if not os.path.isdir(os.path.join(BQ_ROOT, r["db"])):
            continue
        s = spec.get(iid, {"condition_cols": [], "ignore_order": True})
        r["_golds"] = golds
        r["_cc"] = s["condition_cols"]
        r["_io"] = s["ignore_order"]
        out.append(r)
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- #
# Probe: generate -> execute (cost-guarded) -> repair -> score
# --------------------------------------------------------------------------- #
def score(client: BQClient, df: pd.DataFrame, task: dict) -> Tuple[bool, str]:
    try:
        golds = [pd.read_csv(g) for g in task["_golds"]]
    except Exception as e:  # noqa: BLE001
        return False, f"gold read: {e}"
    try:
        return bool(compare_multi_pandas_table(df, golds, task["_cc"], task["_io"])), ""
    except Exception as e:  # noqa: BLE001
        return False, f"compare: {e}"


def run_probe(n: int, dbs, model: str, repair: int, max_gb: float, tag: str):
    tasks = load_bq_tasks(n, dbs)
    client = BQClient(max_gb=max_gb)
    llm = LLM(model=model)
    rows = []
    print(f"BigQuery probe: {len(tasks)} bq tasks | model={model} | cost-guard={max_gb}GB/query\n")
    for t in tasks:
        schema = render_bq_schema(t["db"])
        ev = _evidence(t)
        sql = gen_bq_sql(llm, schema, t["question"], ev)
        df, err = None, "no sql"
        for attempt in range(repair):
            if not sql:
                break
            try:
                df = client.run(sql)
                err = ""
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:200]
                if attempt < repair - 1:
                    sql = gen_bq_sql(llm, schema, t["question"], ev, prior_error=err) or sql
        correct, serr = (score(client, df, t) if df is not None else (False, err))
        rows.append({"instance_id": t["instance_id"], "db": t["db"], "correct": correct,
                     "error": err or serr, "cost_usd_so_far": round(client.cost_usd, 5)})
        print(f"  {t['instance_id']:8} db={t['db']:14} ok={int(correct)} "
              f"scan={client.bytes_billed/1e9:6.2f}GB cost=${client.cost_usd:.4f} "
              f"{('' if correct else (err or serr)[:60])}")

    n_ok = sum(r["correct"] for r in rows)
    print(f"\n=== BigQuery probe summary ===")
    print(f"  tasks:            {len(rows)}")
    print(f"  correct:          {n_ok} ({100*n_ok/max(1,len(rows)):.1f}%)")
    print(f"  queries executed: {client.n_run} | cost-skipped: {client.n_skipped_cost}")
    print(f"  bytes billed:     {client.bytes_billed/1e9:.2f} GB")
    print(f"  REAL COST:        ${client.cost_usd:.4f}")
    if rows:
        print(f"  cost / task:      ${client.cost_usd/len(rows):.4f}  "
              f"-> full 180 bq ≈ ${client.cost_usd/len(rows)*180:.2f} (direct-SQL floor)")
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "skiewsql", "results_real", f"{tag}_bq_probe.json")
    json.dump({"rows": rows, "cost_usd": client.cost_usd, "n_run": client.n_run,
               "bytes_billed": client.bytes_billed}, open(out, "w"), indent=2)
    print(f"\nWrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--dbs", default="", help="comma list of bq db names, or empty for first N")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--repair", type=int, default=3)
    ap.add_argument("--max_gb", type=float, default=5.0)
    ap.add_argument("--tag", default="bqprobe")
    args = ap.parse_args()
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    run_probe(args.n, dbs, args.model, args.repair, args.max_gb, args.tag)


if __name__ == "__main__":
    main()
