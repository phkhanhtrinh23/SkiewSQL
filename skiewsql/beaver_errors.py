#!/usr/bin/env python3
"""
beaver_errors.py — reusable pred-vs-gold error analyzer for the BEAVER runs.

Joins each config's result rows (bv{TAG}_dw_beaver.json) to the gold SQL in the
BEAVER query parquets, extracts the composed CTEs + their seed/online provenance
(from bv{TAG}_dw_beaver_graphs.json and the frozen seed graphs), and reports why a
sample is wrong: column-count deltas, error class, and the reuse footprint.

Usage:
  python -m skiewsql.beaver_errors summary  [--tag S]
  python -m skiewsql.beaver_errors negative [--tag S]          # rows flagged negative_reuse
  python -m skiewsql.beaver_errors sample dw_real_33           # one instance across A/B/S
  python -m skiewsql.beaver_errors wrong    [--tag S --limit 5 --detail]
  python -m skiewsql.beaver_errors dump     [--tag S --out /path.csv]   # every wrong row -> CSV
"""
import argparse
import collections
import glob
import json
import os
import re
from typing import Dict, List, Optional

import pandas as pd

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # noqa: BLE001
    sqlglot = None

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results_real")
QUERY_DIR = "/mnt/win_d/skill_driven_agent_view/beaver_data/beaver-query/data"
SEED_DIR = os.path.join(RESULTS, "seed_graphs", "bvseed_beaver")
TAG2FILE = {"A": "bvA", "B": "bvB", "S": "bvS", "Satom": "bvSatom"}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_gold(splits=("dw_real",)) -> Dict[str, dict]:
    out = {}
    for split in splits:
        for f in glob.glob(os.path.join(QUERY_DIR, f"{split}-*.parquet")):
            df = pd.read_parquet(f)
            for _, r in df.iterrows():
                tbls = r.get("tables")
                if isinstance(tbls, str):
                    try:
                        tbls = json.loads(tbls)
                    except Exception:  # noqa: BLE001
                        tbls = [tbls]
                out[str(r["id"])] = {
                    "question": str(r["question"]),
                    "gold_sql": str(r["sql"]),
                    "gold_tables": list(tbls) if tbls is not None else [],
                }
    return out


def load_rows(tag: str) -> List[dict]:
    p = os.path.join(RESULTS, f"{TAG2FILE[tag]}_dw_beaver.json")
    return json.load(open(p))["rows"]


def load_provenance(tag: str) -> Dict[str, Dict[str, str]]:
    """{db: {view_name: 'seed'|'online'}} from the final graph + frozen seed set."""
    prov: Dict[str, Dict[str, str]] = {}
    gp = os.path.join(RESULTS, f"{TAG2FILE[tag]}_dw_beaver_graphs.json")
    graphs = json.load(open(gp)) if os.path.exists(gp) else {}
    for db, g in graphs.items():
        views = g.get("views", g) if isinstance(g, dict) else {}
        names = set(views.keys()) if isinstance(views, dict) else {v["name"] for v in views}
        seed = set()
        sp = os.path.join(SEED_DIR, f"{db}.json")
        if os.path.exists(sp):
            s = json.load(open(sp))
            sv = s.get("views", s)
            seed = set(sv.keys()) if isinstance(sv, dict) else {v["name"] for v in sv}
        prov[db] = {n: ("seed" if n in seed else "online") for n in names}
    return prov


# --------------------------------------------------------------------------- #
# SQL structure
# --------------------------------------------------------------------------- #
def parse_ctes_and_cols(sql: str):
    """Return (list_of_cte_names, n_final_select_columns). Falls back to regex."""
    if sqlglot is not None:
        try:
            tree = sqlglot.parse_one(sql, read="mysql")
            ctes = [c.alias for c in tree.find_all(exp.CTE)]
            sel = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
            ncol = len(sel.selects) if sel is not None else None
            return ctes, ncol
        except Exception:  # noqa: BLE001
            pass
    ctes = re.findall(r"(?:WITH|,)\s+([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(", sql, re.I)
    return ctes, None


def err_class(row: dict) -> str:
    e = (row.get("error") or "").strip()
    if not e:
        return "ok" if row.get("correct") else "wrong (no error / value mismatch)"
    if e.startswith("col count"):
        return "column-count mismatch"
    if "result mismatch" in e:
        return "result mismatch (same shape, wrong rows/values)"
    if "Unknown column" in e:
        return "SQL error: unknown column (hallucinated col/table)"
    if "gold failed" in e:
        return "gold did not run"
    if "interrupted" in e or "timeout" in e.lower():
        return "timeout"
    return "SQL error: other"


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def cmd_summary(tag: str):
    rows = load_rows(tag)
    wrong = [r for r in rows if not r["correct"]]
    print(f"\n=== config {tag}: {len(rows)} tasks, "
          f"{len(rows)-len(wrong)} correct, {len(wrong)} wrong ===")
    hist = collections.Counter(err_class(r) for r in wrong)
    print("\nfailure classes (wrong rows):")
    for k, v in hist.most_common():
        print(f"  {v:3d}  {k}")
    ur = [r for r in wrong if r.get("used_reuse")]
    nr = [r for r in wrong if r.get("negative_reuse")]
    print(f"\nreuse footprint among WRONG rows: used_reuse={len(ur)}  negative_reuse={len(nr)}")
    urc = [r for r in rows if r.get("used_reuse") and r["correct"]]
    print(f"used_reuse among CORRECT rows: {len(urc)}")


def _diff_block(row: dict, gold: dict, prov: Dict[str, Dict[str, str]]):
    db = row["db"]
    ctes, ncol = parse_ctes_and_cols(row["pred_sql"] or "")
    _, gncol = parse_ctes_and_cols(gold["gold_sql"]) if gold else ([], None)
    tag_ctes = [f"{c}[{prov.get(db, {}).get(c, '?')}]" for c in ctes]
    print(f"  error        : {row.get('error')}")
    print(f"  reuse        : reused={row.get('reused')} seed_reused={row.get('seed_reused')} "
          f"generated={row.get('generated')} negative_reuse={row.get('negative_reuse')} "
          f"graph_views={row.get('graph_views')}")
    print(f"  CTEs in pred : {tag_ctes or '(none)'}")
    print(f"  pred #cols   : {ncol}    gold #cols: {gncol}")


def cmd_sample(instance_id: str, tags: List[str]):
    gold_map = load_gold()
    gold = gold_map.get(instance_id)
    print("=" * 78)
    print(f"INSTANCE {instance_id}")
    if gold:
        print(f"\nQUESTION:\n  {gold['question']}")
        print(f"\nGOLD SQL:\n{gold['gold_sql']}")
        print(f"\nGOLD tables: {gold['gold_tables']}")
    for tag in tags:
        prov = load_provenance(tag)
        row = next((r for r in load_rows(tag) if r["instance_id"] == instance_id), None)
        print("\n" + "-" * 78)
        print(f"[config {tag}]  correct={row['correct'] if row else 'N/A'}")
        if not row:
            print("  (instance not in this config's rows)")
            continue
        _diff_block(row, gold, prov)
        print(f"\n  PRED SQL:\n{row['pred_sql']}")


def cmd_negative(tag: str):
    gold_map = load_gold()
    prov = load_provenance(tag)
    rows = [r for r in load_rows(tag) if r.get("negative_reuse")]
    print(f"\n=== config {tag}: {len(rows)} rows flagged negative_reuse ===")
    for r in rows:
        g = gold_map.get(r["instance_id"], {})
        print("\n" + "-" * 78)
        print(f"{r['instance_id']}  correct={r['correct']}")
        print(f"  Q: {g.get('question', r.get('question'))[:150]}")
        _diff_block(r, g, prov)


def cmd_wrong(tag: str, limit: int, detail: bool):
    gold_map = load_gold()
    prov = load_provenance(tag)
    wrong = [r for r in load_rows(tag) if not r["correct"]]
    print(f"\n=== config {tag}: {len(wrong)} wrong (showing {min(limit, len(wrong))}) ===")
    for r in wrong[:limit]:
        g = gold_map.get(r["instance_id"], {})
        print("\n" + "-" * 78)
        print(f"{r['instance_id']}  [{err_class(r)}]")
        print(f"  Q: {g.get('question', r.get('question',''))[:150]}")
        _diff_block(r, g, prov)
        if detail:
            print(f"\n  GOLD:\n{g.get('gold_sql')}\n\n  PRED:\n{r['pred_sql']}")


def cmd_dump(tag: str, out: str):
    gold_map = load_gold()
    prov = load_provenance(tag)
    recs = []
    for r in load_rows(tag):
        g = gold_map.get(r["instance_id"], {})
        ctes, ncol = parse_ctes_and_cols(r["pred_sql"] or "")
        _, gncol = parse_ctes_and_cols(g["gold_sql"]) if g else ([], None)
        recs.append({
            "instance_id": r["instance_id"], "correct": r["correct"],
            "err_class": err_class(r), "error": r.get("error"),
            "pred_cols": ncol, "gold_cols": gncol,
            "col_delta": (ncol - gncol) if (ncol is not None and gncol is not None) else None,
            "reused": r.get("reused"), "seed_reused": r.get("seed_reused"),
            "generated": r.get("generated"), "negative_reuse": r.get("negative_reuse"),
            "n_ctes": len(ctes),
            "seed_ctes": sum(1 for c in ctes if prov.get(r["db"], {}).get(c) == "seed"),
            "question": g.get("question", r.get("question", "")),
        })
    df = pd.DataFrame(recs)
    if out:
        df.to_csv(out, index=False)
        print(f"wrote {len(df)} rows -> {out}")
    w = df[~df.correct]
    print("\ncol_delta distribution among WRONG rows (pred - gold columns):")
    print(w[w.col_delta.notna()]["col_delta"].value_counts().sort_index().to_string())
    return df


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("summary", "negative"):
        s = sub.add_parser(name)
        s.add_argument("--tag", default="S")
    ss = sub.add_parser("sample")
    ss.add_argument("instance_id")
    ss.add_argument("--configs", default="A,B,S")
    sw = sub.add_parser("wrong")
    sw.add_argument("--tag", default="S")
    sw.add_argument("--limit", type=int, default=5)
    sw.add_argument("--detail", action="store_true")
    sd = sub.add_parser("dump")
    sd.add_argument("--tag", default="S")
    sd.add_argument("--out", default="")
    a = ap.parse_args()
    if a.cmd == "summary":
        cmd_summary(a.tag)
    elif a.cmd == "negative":
        cmd_negative(a.tag)
    elif a.cmd == "sample":
        cmd_sample(a.instance_id, a.configs.split(","))
    elif a.cmd == "wrong":
        cmd_wrong(a.tag, a.limit, a.detail)
    elif a.cmd == "dump":
        cmd_dump(a.tag, a.out)


if __name__ == "__main__":
    main()
