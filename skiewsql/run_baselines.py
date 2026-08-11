"""Driver: run a baseline method (din/dail/chess/reforce) on a benchmark (beaver/spider2lite/bigquery),
reusing that benchmark's schema / executor / scorer so results are directly comparable to configs A/S.

  python -m skiewsql.run_baselines --benchmark spider2lite --method din --limit 135 --tag base
"""
from __future__ import annotations
import argparse, json, os, re, signal, time
from typing import List, Tuple
import numpy as np
import pandas as pd

from skiewsql import baselines
from skiewsql.llm import LLM, Embedder, USAGE

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(_ROOT, "skiewsql", "results_real")
PER_Q = 300


class _QTimeout(BaseException):
    pass


def _alarm(sig, frame):
    raise _QTimeout(f"question exceeded {PER_Q}s")


def _mask(s: str) -> str:
    return re.sub(r"\d+|'[^']*'|\"[^\"]*\"", "_", s or "")


def select_examples(embedder, target_q, pool: List[Tuple[str, str]], k=3):
    """DAIL masked-question similarity: top-k (question, gold_sql) from the same-DB pool."""
    if not pool:
        return []
    try:
        embs = embedder.encode([_mask(q) for q, _ in pool] + [_mask(target_q)])
        tv = np.asarray(embs[-1], dtype=float)
        scored = []
        for i, (q, s) in enumerate(pool):
            v = np.asarray(embs[i], dtype=float)
            cos = float(np.dot(tv, v) / ((np.linalg.norm(tv) * np.linalg.norm(v)) + 1e-9))
            scored.append((cos, q, s))
        scored.sort(key=lambda x: -x[0])
        return [(q, s) for _c, q, s in scored[:k]]
    except Exception:
        return pool[:k]


# --------------------------------------------------------------------------- #
def cases_beaver(limit, dbs=None):
    from skiewsql import beaver_method as bm
    client = bm.MySQLClient()
    tasks = bm._filter_runnable_gold(client, bm.load_beaver_tasks(["dw_real"], limit))
    pool_by_db = {}
    for t in tasks:
        pool_by_db.setdefault(t["db"], []).append((t["question"], t["gold_sql"]))
    schema_cache = {}
    out = []
    for t in tasks:
        db = t["db"]
        schema_cache.setdefault(db, bm.render_mysql_schema(client, db))
        def make(db, t):
            def executor(sql):
                try:
                    return client.run(sql, db), ""
                except Exception as e:  # noqa: BLE001
                    return None, str(e)[:200]
            def run_sql(q):
                return client.run(q, db).head(5).to_string(index=False)
            def score(pred_sql):
                df, _e = executor(pred_sql) if pred_sql else (None, "no sql")
                return bm.score(client, df, t)
            return executor, run_sql, score
        ex, rs, sc = make(db, t)
        pool = [qs for qs in pool_by_db[db] if qs[0] != t["question"]]
        out.append(dict(iid=t["instance_id"], db=db, question=t["question"], evidence=bm._evidence(t),
                        schema=schema_cache[db], api="mysql", executor=ex, run_sql=rs, score=sc, pool=pool))
    return out, client


def cases_spider2(limit, dbs=None):
    from skiewsql import spider2lite, datasets
    qs, root = spider2lite.load_local()
    by_db = {}
    for q in qs:
        by_db.setdefault(q.db_id, []).append(q)
    chosen = list(by_db) if not dbs else [d for d in dbs if d in by_db]
    cons, schema_cache = {}, {}
    pool_by_db = {d: [(x.question, x.gold_sql) for x in by_db[d] if x.gold_sql] for d in chosen}
    out = []
    for d in chosen:
        for q in by_db[d][:limit]:
            if d not in cons:
                cons[d] = datasets.connect(datasets.db_path(root, d, "spider2lite"))
                schema_cache[d] = datasets.render_schema(cons[d])
            con = cons[d]
            def make(con, q):
                def executor(sql):
                    try:
                        rows = datasets.run_sql(con, sql)
                        return pd.DataFrame(list(rows)), ""
                    except Exception as e:  # noqa: BLE001
                        return None, str(e)[:200]
                def run_sql(s):
                    return str(datasets.run_sql(con, s)[:5])[:500]
                def score(pred_sql):
                    return spider2lite.score(con, pred_sql, q) if pred_sql else (False, "no sql")
                return executor, run_sql, score
            ex, rs, sc = make(con, q)
            pool = [p for p in pool_by_db[d] if p[0] != q.question]
            out.append(dict(iid=(q.qid or getattr(q, "instance_id", "")), db=d, question=q.question,
                            evidence=q.evidence, schema=schema_cache[d], api="sqlite",
                            executor=ex, run_sql=rs, score=sc, pool=pool))
    return out, None


def cases_bigquery(limit, dbs=None):
    from skiewsql.spider2bq import BQClient, bq_table_blocks, load_bq_tasks, score as bq_score, _evidence
    from skiewsql import table_catalog
    client = BQClient(max_gb=2.0)
    llm = LLM(model="gpt-5-mini")
    tasks = load_bq_tasks(limit)
    if dbs:
        tasks = [t for t in tasks if t["db"] in dbs]
    out = []
    for t in tasks:
        db = t["db"]
        blocks = bq_table_blocks(db)
        catalog = table_catalog.build_catalog(llm, db, blocks)
        picked = table_catalog.shortlist(llm, t["question"], catalog, k=8, evidence=_evidence(t))
        schema = table_catalog.render_selected(blocks, picked, budget=24000)
        def make(t):
            def executor(sql):
                try:
                    return client.run(sql, sleep_s=0.0), ""
                except Exception as e:  # noqa: BLE001
                    return None, str(e)[:200]
            def run_sql(q):
                ok, err, _c, gb = client.dry(q)
                if not ok:
                    raise RuntimeError(err)
                if gb > 2.0:
                    raise RuntimeError(f"probe scans {gb:.2f}GB>2GB")
                return client.run(q, cap_rows=5).to_string(index=False)
            def score(pred_sql):
                df, _e = executor(pred_sql) if pred_sql else (None, "no sql")
                return bq_score(client, df, t)
            return executor, run_sql, score
        ex, rs, sc = make(t)
        out.append(dict(iid=t["instance_id"], db=db, question=t["question"], evidence=_evidence(t),
                        schema=schema, api="bigquery", executor=ex, run_sql=rs, score=sc, pool=[]))
    return out, client


def cases_livesql(limit, dbs=None):
    """LiveSQLBench (PostgreSQL) adapter — reuses the livesql_method PG client / schema / scorer so the
    baselines run on the same DBs + gold as config A. api='postgresql'; DAIL pool = other (question,
    gold sol_sql) in the same DB."""
    from skiewsql import livesql_method as lm, table_catalog
    tasks = json.load(open(os.path.join(lm.BASE, "tasks.json")))
    if dbs:
        tasks = [t for t in tasks if t["db"] in dbs]
    tasks = tasks[:limit] if limit else tasks
    client = lm.PGClient()
    pool_by_db = {}
    for t in tasks:
        g = (t.get("sol_sql") or [None])[0]
        if g:
            pool_by_db.setdefault(t["db"], []).append((t["question"], g))
    schema_cache, out = {}, []
    for t in tasks:
        db = t["db"]
        if db not in schema_cache:
            blocks = lm.pg_table_blocks(db)
            schema_cache[db] = table_catalog.render_selected(blocks, list(blocks), budget=24000) if blocks else ""

        def make(db, t):
            def executor(sql):
                try:
                    return pd.DataFrame(client.run(db, sql)), ""
                except Exception as e:  # noqa: BLE001
                    try: client.con(db).rollback()
                    except Exception: pass
                    return None, str(e)[:200]

            def run_sql(q):
                try:
                    return str(client.run(db, q, limit=5))[:500]
                except Exception as e:  # noqa: BLE001
                    return f"(probe failed: {str(e)[:80]})"

            def score(pred_sql):
                return lm._score(client, db, pred_sql, t.get("sol_sql") or [])
            return executor, run_sql, score
        ex, rs, sc = make(db, t)
        pool = [p for p in pool_by_db.get(db, []) if p[0] != t["question"]]
        out.append(dict(iid=t["instance_id"], db=db, question=t["question"], evidence=t.get("evidence", ""),
                        schema=schema_cache[db], api="postgresql", executor=ex, run_sql=rs, score=sc, pool=pool))
    return out, client


ADAPTERS = {"beaver": cases_beaver, "spider2lite": cases_spider2, "bigquery": cases_bigquery,
            "livesql": cases_livesql}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True, choices=list(ADAPTERS))
    ap.add_argument("--method", required=True, choices=list(baselines.METHODS))
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--dbs", default="")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--tag", default="base")
    args = ap.parse_args()

    dbs = [d.strip() for d in args.dbs.split(",") if d.strip()] or None
    llm = LLM(model=args.model)
    embedder = Embedder()
    method_fn = baselines.METHODS[args.method]
    cases, _client = ADAPTERS[args.benchmark](args.limit, dbs)
    print(f"[{args.method} / {args.benchmark}] {len(cases)} cases", flush=True)
    signal.signal(signal.SIGALRM, _alarm)

    rows = []
    for i, c in enumerate(cases):
        USAGE_before = USAGE.total
        t0 = time.time()
        signal.alarm(PER_Q)
        try:
            kw = {}
            if args.method == "dail":
                kw["examples"] = select_examples(embedder, c["question"], c["pool"], k=3)
            if args.method == "reforce":
                kw["run_sql"] = c["run_sql"]
            pred = method_fn(llm, c["schema"], c["question"], c["evidence"], api=c["api"],
                             executor=c["executor"], **kw)
            ok, err = c["score"](pred)
        except (_QTimeout, Exception) as e:  # noqa: BLE001
            pred, ok, err = None, False, f"{type(e).__name__}: {str(e)[:120]}"
        finally:
            signal.alarm(0)
        rows.append(dict(instance_id=c["iid"], db=c["db"], question=c["question"],
                         correct=bool(ok), pred_sql=pred, error=("" if ok else str(err)[:200]),
                         tokens=USAGE.total - USAGE_before, secs=round(time.time() - t0, 1)))
        nok = sum(r["correct"] for r in rows)
        print(f"  {str(c['iid'])[:16]:16} {c['db'][:14]:14} ok={int(bool(ok))} "
              f"[{nok}/{len(rows)}={100*nok/len(rows):.1f}%] {('' if ok else str(err)[:45])}", flush=True)
        if i % 20 == 0:
            json.dump(rows, open(os.path.join(RESULTS_DIR, f"{args.tag}_{args.method}_{args.benchmark}.json"), "w"), indent=1)

    n = len(rows); ok = sum(r["correct"] for r in rows)
    json.dump(rows, open(os.path.join(RESULTS_DIR, f"{args.tag}_{args.method}_{args.benchmark}.json"), "w"), indent=1)
    print(f"\n=== {args.method} / {args.benchmark}: {ok}/{n} = {100*ok/max(n,1):.1f}% ===", flush=True)


if __name__ == "__main__":
    main()
