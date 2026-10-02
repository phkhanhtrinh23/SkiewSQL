"""run.py — sequential SkiewSQL experiment over the retail DB. Runs three configurations and reports the metrics requested in the design: (A) SkiewSQL         : view memory ON, negative-reuse guard ON   (our method) (B) Baseline (AV-SQL) : view memory OFF -> regenerate every CTE per question, discard (C) SkiewSQL no-guard: memory ON, compatibility guard OFF        (ablation -> negative reuse)

Everything executes against a real SQLite DB. Execution accuracy compares result sets of the composed SQL vs an independent gold SQL. No LLM / no network.

    python -m skiewsql.run"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import sqlite3

from skiewsql.build_db import build, DB_DEFAULT
from skiewsql.bench import LIBRARY, QUESTIONS, request_for
from skiewsql.core import ViewGraph, retrieve, validate_view, compose_sql

EST_TOKENS_PER_VIEW = 1500   # proxy: avg tokens to generate+validate one CTE with an LLM
RESULTS_DIR = os.path.join(_ROOT, "skiewsql", "results")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def exec_sql(con, sql):
    cur = con.execute(sql)
    return cur.fetchall()


def normalize(rows, order_sensitive):
    norm = [tuple(round(x, 2) if isinstance(x, float) else x for x in row) for row in rows]
    if not order_sensitive:
        norm = sorted(norm, key=repr)
    return norm


def build_view(graph: ViewGraph, con, name, gen_log):
    """Recursively instantiate `name` (and its deps) from the library. Validate by execution."""
    if graph.has(name):
        return 0
    n_built = 0
    spec = LIBRARY[name]
    for dep in spec.depends_on:
        n_built += build_view(graph, con, dep, gen_log)
    graph.add_view(spec)
    ok, msg = validate_view(con, graph, spec)
    gen_log.append({"view": name, "valid": ok, "msg": msg})
    if not ok:
        raise RuntimeError(f"view {name} failed validation: {msg}")
    return n_built + 1


def answer_question(graph: ViewGraph, con, q, *, use_memory, use_guard, tau=0.15):
    wants = q["wants"]
    chosen, reused_cnt, generated = {}, 0, 0
    diagnostics = []
    for want in wants:
        req = request_for(want, text=q["text"] + " " + LIBRARY[want].description)
        hit_spec, diag = (None, {"hit": False, "reason": "memory-off"})
        if use_memory:
            hit_spec, diag = retrieve(graph, req, tau=tau, use_guard=use_guard)
        diagnostics.append({want: diag})
        if hit_spec is not None:
            chosen[want] = hit_spec.name
            reused_cnt += 1
        else:
            generated += build_view(graph, con, want, gen_log=[])
            chosen[want] = want
    final = q["final"].format(**chosen)
    composed = compose_sql(graph, sorted(set(chosen.values())), final)
    try:
        got = normalize(exec_sql(con, composed), q["order_sensitive"])
        gold = normalize(exec_sql(con, q["gold"]), q["order_sensitive"])
        correct = got == gold
        err = None
    except Exception as e:  # noqa: BLE001
        correct, err = False, f"{type(e).__name__}: {e}"
    used_reuse = reused_cnt > 0
    return {
        "id": q["id"], "n_wants": len(wants), "reused": reused_cnt, "generated": generated,
        "coverage": reused_cnt / len(wants), "no_new_cte": generated == 0,
        "correct": correct, "used_reuse": used_reuse,
        "negative_reuse": used_reuse and not correct,
        "error": err, "diag": diagnostics, "composed": composed,
    }


def run_config(name, *, use_memory, use_guard, fresh_db):
    con = sqlite3.connect(fresh_db)
    graph = ViewGraph(db_id="retail")
    rows, cum_gen = [], 0
    for q in QUESTIONS:
        if not use_memory:                 # baseline: discard memory before each question
            graph = ViewGraph(db_id="retail")
        r = answer_question(graph, con, q, use_memory=use_memory, use_guard=use_guard)
        cum_gen += r["generated"]
        r["cum_generated"] = cum_gen
        r["graph_views"] = graph.n_views()
        rows.append(r)
    con.close()

    n = len(rows)
    total_wants = sum(r["n_wants"] for r in rows)
    total_reused = sum(r["reused"] for r in rows)
    total_gen = sum(r["generated"] for r in rows)
    acc = sum(r["correct"] for r in rows) / n
    summary = {
        "config": name,
        "questions": n,
        "exec_accuracy": round(acc, 4),
        "cold_start_acc": rows[0]["correct"],
        "warm_acc": round(sum(r["correct"] for r in rows[1:]) / (n - 1), 4),
        "exact_reuse_rate": round(total_reused / total_wants, 4),
        "pct_no_new_cte": round(sum(r["no_new_cte"] for r in rows) / n, 4),
        "total_views_generated": total_gen,
        "avg_new_views_per_q": round(total_gen / n, 3),
        "token_proxy": total_gen * EST_TOKENS_PER_VIEW,
        "negative_reuse_count": sum(r["negative_reuse"] for r in rows),
        "final_graph_size": rows[-1]["graph_views"] if use_memory else 0,
    }
    return summary, rows


def pct(x):
    return f"{100 * x:5.1f}%"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    db = build(DB_DEFAULT)
    print(f"\nBuilt DB: {db}")
    con = sqlite3.connect(db)
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["stores", "customers", "products", "orders", "order_items", "employees"]}
    con.close()
    print("Row counts:", counts)
    print(f"Questions in stream: {len(QUESTIONS)}   View library size: {len(LIBRARY)}\n")

    configs = [
        ("A_SkiewSQL",          dict(use_memory=True,  use_guard=True)),
        ("B_Baseline_AVSQL",     dict(use_memory=False, use_guard=True)),
        ("C_SkiewSQL_noguard",  dict(use_memory=True,  use_guard=False)),
    ]
    all_summaries, all_rows = {}, {}
    for cname, kw in configs:
        s, rows = run_config(cname, fresh_db=db, **kw)
        all_summaries[cname] = s
        all_rows[cname] = rows

    # ---- per-question trace for the main method -------------------------------
    print("=" * 78)
    print("PER-QUESTION TRACE — (A) SkiewSQL  [memory ON, guard ON]")
    print("=" * 78)
    print(f"{'Q':4} {'wants':5} {'reuse':5} {'gen':3} {'cumGen':6} {'graph':5} {'noNewCTE':8} {'correct'}")
    for r in all_rows["A_SkiewSQL"]:
        print(f"{r['id']:4} {r['n_wants']:^5} {r['reused']:^5} {r['generated']:^3} "
              f"{r['cum_generated']:^6} {r['graph_views']:^5} {str(r['no_new_cte']):^8} {r['correct']}")

    # ---- summary comparison ---------------------------------------------------
    print("\n" + "=" * 78)
    print("SUMMARY — three configurations")
    print("=" * 78)
    keys = [
        ("exec_accuracy", "Execution accuracy"),
        ("cold_start_acc", "Cold-start acc (Q01)"),
        ("warm_acc", "Warm acc (Q02..)"),
        ("exact_reuse_rate", "Exact view-reuse rate"),
        ("pct_no_new_cte", "% Q with no new CTE"),
        ("total_views_generated", "Total CTE generations"),
        ("avg_new_views_per_q", "Avg new views / Q"),
        ("token_proxy", "Token proxy (gen)"),
        ("negative_reuse_count", "Negative-reuse count"),
        ("final_graph_size", "Final graph size"),
    ]
    cols = ["A_SkiewSQL", "B_Baseline_AVSQL", "C_SkiewSQL_noguard"]
    print(f"{'metric':24} " + " ".join(f"{c:>20}" for c in cols))
    for k, label in keys:
        vals = []
        for c in cols:
            v = all_summaries[c][k]
            if k in ("exec_accuracy", "cold_start_acc", "warm_acc", "exact_reuse_rate", "pct_no_new_cte"):
                vals.append(pct(v) if not isinstance(v, bool) else str(v))
            else:
                vals.append(str(v))
        print(f"{label:24} " + " ".join(f"{x:>20}" for x in vals))

    # ---- efficiency takeaways -------------------------------------------------
    a, b = all_summaries["A_SkiewSQL"], all_summaries["B_Baseline_AVSQL"]
    saved = b["total_views_generated"] - a["total_views_generated"]
    print("\n" + "-" * 78)
    print(f"SkiewSQL generated {a['total_views_generated']} CTEs vs baseline "
          f"{b['total_views_generated']}  ->  {saved} fewer "
          f"({pct(saved / b['total_views_generated'])} reduction, "
          f"~{saved * EST_TOKENS_PER_VIEW:,} fewer generation tokens).")
    print(f"Negative-reuse with guard ON: {a['negative_reuse_count']}   |   "
          f"guard OFF: {all_summaries['C_SkiewSQL_noguard']['negative_reuse_count']} "
          f"(accuracy {pct(all_summaries['C_SkiewSQL_noguard']['exec_accuracy'])}).")

    # ---- persist --------------------------------------------------------------
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(all_summaries, f, indent=2)
    # learning curve CSV (config A)
    with open(os.path.join(RESULTS_DIR, "learning_curve.csv"), "w") as f:
        f.write("q_index,q_id,generated,cum_generated,reused,coverage,correct\n")
        for i, r in enumerate(all_rows["A_SkiewSQL"], 1):
            f.write(f"{i},{r['id']},{r['generated']},{r['cum_generated']},{r['reused']},"
                    f"{r['coverage']:.3f},{int(r['correct'])}\n")
    with open(os.path.join(RESULTS_DIR, "per_question_A.json"), "w") as f:
        json.dump([{k: v for k, v in r.items() if k != "diag"} for r in all_rows["A_SkiewSQL"]],
                  f, indent=2)
    print(f"\nWrote: {RESULTS_DIR}\\summary.json, learning_curve.csv, per_question_A.json")


if __name__ == "__main__":
    main()
