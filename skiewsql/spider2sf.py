"""
spider2sf.py — Snowflake execution backend + probe for the Spider 2.0-lite `sf*` tasks
(the 207 cloud-only Snowflake tasks over 58 shared databases).

Mirrors spider2bq.py: generate Snowflake SQL from the schema DDL → execute on Snowflake
(statement-timeout + row-cap guarded) → score against the gold result CSV with the official
Spider2 comparison. Purpose: (a) prove the Snowflake backend works, (b) measure per-task
runtime/latency before committing to the full 207-task / view-memory run.

Snowflake specifics handled here:
  * auth via Programmatic Access Token (PAT) read from the evaluation_suite folder;
  * STATEMENT_TIMEOUT_IN_SECONDS session guard + capped fetch (no runaway queries);
  * result DataFrame is round-tripped through CSV before comparison, exactly like the
    official evaluate.py (which saves result.csv and re-reads it) — this normalises
    Decimal/date/timestamp cells the same way the official scorer sees them;
  * EXPLAIN-based validation (compiles without running the query — used as the free
    validation step by the view-memory method, analogous to BigQuery dry-run);
  * schema rendering walks resource/databases/snowflake/<DB>/<SCHEMA>/DDL.csv and emits
    fully-qualified names; column identifiers in these DBs are lowercase-and-quoted, which
    the generation prompt calls out explicitly.
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd
import snowflake.connector

from skiewsql.llm import LLM, extract_code
from skiewsql.spider2lite import (compare_pandas_table, compare_multi_pandas_table,
                                  _eval_spec, _gold_csvs, QUESTIONS, DOCS_DIR)

SP2 = "/mnt/win_d/Multilingual_Text_to_SQL_code_backend/Spider2/spider2-lite"
SF_ROOT = os.path.join(SP2, "resource", "databases", "snowflake")
CRED = os.path.join(SP2, "evaluation_suite", "snowflake_credential.json")
PAT = os.path.join(SP2, "evaluation_suite", "snowflake_pat.txt")

STMT_TIMEOUT_S = 180         # server-side statement timeout (kills runaway queries)
MAX_ROWS = 100000            # capped fetch


# --------------------------------------------------------------------------- #
# Snowflake client (PAT auth, timeout + row-cap guards, exec accounting)
# --------------------------------------------------------------------------- #
class SFClient:
    def __init__(self, cred: str = CRED, pat: str = PAT, timeout_s: int = STMT_TIMEOUT_S,
                 warehouse: str = "COMPUTE_WH_PARTICIPANT"):
        c = json.load(open(cred))
        token = open(pat).read().strip()
        self.con = snowflake.connector.connect(
            user=c["user"], account=c["account"], password=token,
            warehouse=warehouse, login_timeout=60, network_timeout=60)
        cur = self.con.cursor()
        cur.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout_s}")
        cur.close()
        self.n_run = 0
        self.n_explain = 0
        self.exec_seconds = 0.0

    def describe(self, sql: str) -> Tuple[bool, str, List[str]]:
        """FREE validation (compilation only, no execution — the analogue of BigQuery
        dry-run): returns (valid, error, result_columns)."""
        cur = self.con.cursor()
        try:
            meta = cur.describe(sql)
            self.n_explain += 1
            return True, "", [m.name for m in (meta or [])]
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {str(e)[:300]}", []
        finally:
            cur.close()

    def explain(self, sql: str) -> Tuple[bool, str]:
        """FREE-ish validation: EXPLAIN compiles the query without executing it.
        Returns (valid, error)."""
        cur = self.con.cursor()
        try:
            cur.execute("EXPLAIN USING TEXT " + sql)
            cur.fetchall()
            self.n_explain += 1
            return True, ""
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {str(e)[:300]}"
        finally:
            cur.close()

    def run(self, sql: str, cap_rows: int = MAX_ROWS, sleep_s: float = 0.0) -> pd.DataFrame:
        t0 = time.time()
        cur = self.con.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchmany(cap_rows + 1)
            if len(rows) > cap_rows:
                raise RuntimeError(f"result too large (>{cap_rows} rows)")
            cols = [d[0] for d in cur.description] if cur.description else []
        finally:
            cur.close()
            self.exec_seconds += time.time() - t0
        self.n_run += 1
        if sleep_s:
            time.sleep(sleep_s)
        df = pd.DataFrame(rows, columns=cols)
        # CSV round-trip = exactly what the official evaluate.py compares (it saves
        # result.csv then re-reads it): normalises Decimal/date/timestamp/None cells.
        if df.empty:
            return df
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return pd.read_csv(buf)

    def close(self):
        try:
            self.con.close()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# Schema rendering (per-schema DDL blocks with fully-qualified headers)
# --------------------------------------------------------------------------- #
def _stem(name: str) -> str:
    """Collapse year/date-sharded table families (e.g. BLOCKGROUP_2010_5YR) to one stem."""
    s = re.sub(r"(19|20)\d{6}", "<YYYYMMDD>", name)
    s = re.sub(r"(19|20)\d{4}", "<YYYYMM>", s)
    s = re.sub(r"(19|20)\d{2}", "<YYYY>", s)
    s = re.sub(r"\d+$", "<N>", s)
    return s


def sf_table_blocks(db: str) -> Dict[str, str]:
    """{table_stem: CREATE TABLE DDL} for a Snowflake DB, sharded siblings collapsed to one
    representative. Mirrors spider2bq.bq_table_blocks so the N×M chunk-select / description-catalog
    path (table_catalog.build_catalog/shortlist/render_selected) works for Snowflake too — replacing
    the 16k-char truncation in render_sf_schema. Each DDL is headed by the fully-qualified
    <DB>.<SCHEMA>.<TABLE> the query must address."""
    out: Dict[str, str] = {}
    for ddlcsv in sorted(glob.glob(os.path.join(SF_ROOT, db, "*", "DDL.csv"))):
        schema = os.path.basename(os.path.dirname(ddlcsv))
        seen: set = set()
        try:
            for row in csv.DictReader(open(ddlcsv, encoding="utf-8", errors="ignore")):
                if not row.get("DDL"):
                    continue
                name = row.get("table_name", "") or ""
                st = _stem(name) or name
                if st in seen:                                # collapse sharded siblings
                    continue
                seen.add(st)
                out[st] = f"-- {db}.{schema}.{name}\n{row['DDL']}"
        except Exception:  # noqa: BLE001
            continue
    return out


def render_sf_schema(db: str, max_chars: int = 16000) -> str:
    """Concatenate CREATE TABLE DDLs for a Snowflake database, one block per schema,
    headed by the fully-qualified <DB>.<SCHEMA> prefix the tables must be addressed with.
    Year/date-sharded table families are collapsed to one representative DDL. If still
    truncated, appends the complete list of fully-qualified table names."""
    blocks: List[str] = []
    fq_names: List[str] = []
    for ddlcsv in sorted(glob.glob(os.path.join(SF_ROOT, db, "*", "DDL.csv"))):
        schema = os.path.basename(os.path.dirname(ddlcsv))
        parts = [f"-- Tables below live in {db}.{schema} "
                 f"(address as {db}.{schema}.<TABLE>)"]
        seen: Dict[str, int] = {}
        try:
            for row in csv.DictReader(open(ddlcsv, encoding="utf-8", errors="ignore")):
                if not row.get("DDL"):
                    continue
                name = row.get("table_name", "")
                fq_names.append(f"{db}.{schema}.{name}")
                st = _stem(name)
                if st in seen:
                    seen[st] += 1
                    continue
                seen[st] = 1
                parts.append(row["DDL"])
        except Exception:  # noqa: BLE001
            continue
        shards = [f"{st} (+{n - 1} siblings)" for st, n in seen.items() if n > 1]
        if shards:
            parts.append("-- year/date-sharded table families in this schema "
                         "(one representative DDL shown above): " + "; ".join(shards[:20]))
        blocks.append("\n\n".join(parts))
    text = "\n\n".join(blocks)
    if len(text) > max_chars:
        listing = "\n\n-- ALL tables (fully qualified): " + ", ".join(fq_names)
        text = text[:max_chars - min(len(listing), 4000)] + listing[:4000]
    return text


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
# Snowflake SQL generation (dialect-aware)
# --------------------------------------------------------------------------- #
GEN_SYS = (
    "You are a Snowflake SQL generator. Given the schema (Snowflake DDL) and a question, write "
    "ONE executable Snowflake query. Use fully-qualified table names DATABASE.SCHEMA.TABLE exactly "
    "as given in the schema headers. CRITICAL QUOTING RULES: base-table column identifiers are "
    "lowercase and case-sensitive — double-quote them exactly as in the DDL (e.g. "
    "\"block_timestamp\") EVERY time you touch the base table. Whenever a CTE/subquery selects a "
    "base column, ALIAS it to an unquoted name (e.g. SELECT \"country_code\" AS country_code) and "
    "refer ONLY to that unquoted alias downstream — never reference a quoted-lowercase name "
    "without quotes. For VARIANT columns use : path access and LATERAL FLATTEN. "
    "No backticks. Output one ```sql block only, no explanation."
)
GEN_USER = """Snowflake schema (DDL):
{schema}

Question: {question}
{evidence}
{error}
```sql
SELECT ...
```"""


def gen_sf_sql(llm: LLM, schema: str, question: str, evidence: str,
               prior_error: Optional[str] = None) -> Optional[str]:
    err = f"\nThe previous query failed with:\n{prior_error}\nFix it." if prior_error else ""
    txt = llm.ask(GEN_SYS, GEN_USER.format(schema=schema, question=question, evidence=evidence,
                                           error=err), tag="sf_gen", max_tokens=1400)
    sql = extract_code(txt, langs=("sql",))
    return sql.strip().rstrip(";") if sql else None


# --------------------------------------------------------------------------- #
# Load sf tasks (only those with a gold CSV, so they are scorable)
# --------------------------------------------------------------------------- #
def load_sf_tasks(limit: int = 10 ** 9, dbs: Optional[List[str]] = None) -> List[dict]:
    spec = _eval_spec()
    out = []
    for line in open(QUESTIONS):
        line = line.strip()
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        iid = r["instance_id"]
        if not iid.startswith("sf"):
            continue
        if dbs and r["db"] not in dbs:
            continue
        golds = _gold_csvs(iid)
        if not golds:
            continue
        if not os.path.isdir(os.path.join(SF_ROOT, r["db"])):
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
# Probe: generate -> execute (guarded) -> repair -> score
# --------------------------------------------------------------------------- #
def score(df: pd.DataFrame, task: dict) -> Tuple[bool, str]:
    try:
        golds = [pd.read_csv(g) for g in task["_golds"]]
    except Exception as e:  # noqa: BLE001
        return False, f"gold read: {e}"
    try:
        # match official evaluate.py: single gold -> compare_pandas_table (condition_cols
        # applied as-is); multiple gold variants -> compare_multi (broadcasts them).
        if len(golds) == 1:
            ok = compare_pandas_table(df, golds[0], task["_cc"], task["_io"])
        else:
            ok = compare_multi_pandas_table(df, golds, task["_cc"], task["_io"])
        return bool(ok), ""
    except Exception as e:  # noqa: BLE001
        return False, f"compare: {e}"


def run_probe(n: int, dbs, model: str, repair: int, tag: str, sleep_s: float = 1.0):
    tasks = load_sf_tasks(n, dbs)
    client = SFClient()
    llm = LLM(model=model)
    rows = []
    print(f"Snowflake probe: {len(tasks)} sf tasks | model={model} | "
          f"timeout={STMT_TIMEOUT_S}s/query\n")
    for t in tasks:
        schema = render_sf_schema(t["db"])
        ev = _evidence(t)
        sql = gen_sf_sql(llm, schema, t["question"], ev)
        df, err = None, "no sql"
        for attempt in range(repair):
            if not sql:
                break
            ok, derr, _cols = client.describe(sql)       # FREE compile check first
            if not ok:
                err = derr[:250]
                if attempt < repair - 1:
                    sql = gen_sf_sql(llm, schema, t["question"], ev, prior_error=err) or sql
                continue
            try:
                df = client.run(sql, sleep_s=sleep_s)
                err = ""
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)[:250]
                df = None
                if attempt < repair - 1:
                    sql = gen_sf_sql(llm, schema, t["question"], ev, prior_error=err) or sql
        correct, serr = (score(df, t) if df is not None else (False, err))
        rows.append({"instance_id": t["instance_id"], "db": t["db"], "correct": correct,
                     "error": err or serr, "sql": sql,
                     "exec_s_so_far": round(client.exec_seconds, 1)})
        print(f"  {t['instance_id']:10} db={t['db'][:22]:22} ok={int(correct)} "
              f"exec={client.exec_seconds:6.1f}s "
              f"{('' if correct else (err or serr)[:70])}")

    n_ok = sum(r["correct"] for r in rows)
    print(f"\n=== Snowflake probe summary ===")
    print(f"  tasks:            {len(rows)}")
    print(f"  correct:          {n_ok} ({100*n_ok/max(1,len(rows)):.1f}%)")
    print(f"  queries executed: {client.n_run}")
    print(f"  exec time:        {client.exec_seconds:.1f}s "
          f"({client.exec_seconds/max(1,len(rows)):.1f}s/task)")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "results_real", f"{tag}_sf_probe.json")
    json.dump({"rows": rows, "n_run": client.n_run,
               "exec_seconds": client.exec_seconds}, open(out, "w"), indent=2)
    print(f"\nWrote {out}")
    client.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--dbs", default="", help="comma list of sf db names, or empty for first N")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--repair", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--tag", default="sfprobe")
    args = ap.parse_args()
    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    run_probe(args.n, dbs, args.model, args.repair, args.tag, args.sleep)


if __name__ == "__main__":
    main()
