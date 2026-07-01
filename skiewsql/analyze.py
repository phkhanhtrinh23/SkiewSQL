"""
analyze.py — read realrun.py outputs and produce learning-curve figures + a markdown
report comparing SkiewSQL (A) vs Baseline AV-SQL (B) vs no-guard (C).

  python -m skiewsql.analyze --tag exp1 --dataset spider

Reads skiewsql/results_real/{tag}_{dataset}_{Config}.json and writes figures + report
to the same directory.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(_ROOT, "skiewsql", "results_real")


def load_configs(tag, dataset):
    out = {}
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, f"{tag}_{dataset}_*.json"))):
        if path.endswith("_summary.json"):
            continue
        d = json.load(open(path))
        out[d["summary"]["config"]] = d
    return out


def cumulative_by_index(rows, field):
    """Average cumulative `field` across DBs, indexed by within-DB question index."""
    per_db = defaultdict(dict)        # db -> {index: cum_value}
    acc = defaultdict(float)
    for r in sorted(rows, key=lambda r: (r["db_id"], r["db_index"])):
        acc[r["db_id"]] += r[field]
        per_db[r["db_id"]][r["db_index"]] = acc[r["db_id"]]
    # average across dbs at each index
    max_i = max(r["db_index"] for r in rows)
    xs, ys = [], []
    for i in range(max_i + 1):
        vals = [per_db[db][i] for db in per_db if i in per_db[db]]
        if vals:
            xs.append(i)
            ys.append(sum(vals) / len(vals))
    return xs, ys


def rolling_accuracy(rows):
    per_db = defaultdict(list)
    for r in sorted(rows, key=lambda r: (r["db_id"], r["db_index"])):
        per_db[r["db_id"]].append(r["correct"])
    max_i = max(len(v) for v in per_db.values())
    xs, ys = [], []
    for i in range(max_i):
        vals = []
        for db, corr in per_db.items():
            if i < len(corr):
                vals.append(sum(corr[:i + 1]) / (i + 1))
        if vals:
            xs.append(i)
            ys.append(100 * sum(vals) / len(vals))
    return xs, ys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="exp1")
    ap.add_argument("--dataset", default="spider")
    args = ap.parse_args()
    cfgs = load_configs(args.tag, args.dataset)
    if not cfgs:
        print("No result files found for", args.tag, args.dataset)
        return
    colors = {"A_SkiewSQL": "#1f77b4", "B_Baseline_AVSQL": "#d62728",
              "C_SkiewSQL_noguard": "#2ca02c"}
    labels = {"A_SkiewSQL": "SkiewSQL (memory+guard)",
              "B_Baseline_AVSQL": "Baseline AV-SQL (no memory)",
              "C_SkiewSQL_noguard": "SkiewSQL (guard off)"}

    # ---- Figure 1: cumulative CTE generations vs question index --------------
    plt.figure(figsize=(7, 4.5))
    for name, d in cfgs.items():
        xs, ys = cumulative_by_index(d["rows"], "generated")
        plt.plot(xs, ys, marker="o", ms=3, label=labels.get(name, name),
                 color=colors.get(name))
    plt.xlabel("question index within database (sequential)")
    plt.ylabel("cumulative CTE views generated (avg over DBs)")
    plt.title(f"View generation cost vs questions seen — {args.dataset}")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    f1 = os.path.join(RESULTS_DIR, f"{args.tag}_{args.dataset}_gen_curve.png")
    plt.savefig(f1, dpi=130)
    plt.close()

    # ---- Figure 2: cumulative tokens vs question index -----------------------
    plt.figure(figsize=(7, 4.5))
    for name, d in cfgs.items():
        xs, ys = cumulative_by_index(d["rows"], "tokens")
        plt.plot(xs, [y / 1000 for y in ys], marker="o", ms=3,
                 label=labels.get(name, name), color=colors.get(name))
    plt.xlabel("question index within database (sequential)")
    plt.ylabel("cumulative tokens (thousands, avg over DBs)")
    plt.title(f"Token cost vs questions seen — {args.dataset}")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    f2 = os.path.join(RESULTS_DIR, f"{args.tag}_{args.dataset}_token_curve.png")
    plt.savefig(f2, dpi=130)
    plt.close()

    # ---- markdown report -----------------------------------------------------
    order = [c for c in ["A_SkiewSQL", "B_Baseline_AVSQL", "C_SkiewSQL_noguard"] if c in cfgs]
    rep = [f"# SkiewSQL results — {args.dataset} (tag={args.tag})\n"]
    s0 = cfgs[order[0]]["summary"]
    rep.append(f"Databases: {list(s0['final_graph_sizes'])}  |  "
               f"questions/config: {s0['questions']}\n")
    metrics = [
        ("exec_accuracy", "Execution accuracy", "pct"),
        ("cold_start_acc", "Cold-start EX (1st Q/db)", "pct"),
        ("warm_acc", "Warm EX (later Qs)", "pct"),
        ("exact_reuse_rate", "Exact view-reuse rate", "pct"),
        ("pct_no_new_cte", "% Q with no new CTE", "pct"),
        ("total_views_generated", "Total CTE generations", "int"),
        ("avg_new_views_per_q", "Avg new views / Q", "num"),
        ("real_total_tokens", "REAL total tokens", "int"),
        ("negative_reuse_count", "Negative-reuse count", "int"),
        ("avg_secs_per_q", "Avg secs / Q", "num"),
    ]
    rep.append("| metric | " + " | ".join(labels.get(c, c) for c in order) + " |")
    rep.append("|---|" + "---|" * len(order))
    for key, label, kind in metrics:
        cells = []
        for c in order:
            v = cfgs[c]["summary"][key]
            if kind == "pct":
                cells.append(f"{100*v:.1f}%" if isinstance(v, (int, float)) else str(v))
            else:
                cells.append(str(v))
        rep.append(f"| {label} | " + " | ".join(cells) + " |")
    # efficiency takeaway
    if "A_SkiewSQL" in cfgs and "B_Baseline_AVSQL" in cfgs:
        a, b = cfgs["A_SkiewSQL"]["summary"], cfgs["B_Baseline_AVSQL"]["summary"]
        dg = b["total_views_generated"] - a["total_views_generated"]
        dt = b["real_total_tokens"] - a["real_total_tokens"]
        rep.append("")
        if b["total_views_generated"]:
            rep.append(f"- **CTE generations**: {a['total_views_generated']} (SkiewSQL) vs "
                       f"{b['total_views_generated']} (baseline) → {dg} fewer "
                       f"({100*dg/b['total_views_generated']:.1f}% reduction).")
        if b["real_total_tokens"]:
            rep.append(f"- **Real tokens**: {a['real_total_tokens']:,} vs {b['real_total_tokens']:,} "
                       f"→ {dt:,} fewer ({100*dt/b['real_total_tokens']:.1f}% reduction).")
        rep.append(f"- **Accuracy**: {100*a['exec_accuracy']:.1f}% (SkiewSQL) vs "
                   f"{100*b['exec_accuracy']:.1f}% (baseline).")
    # ---- per-stage token breakdown (mirrors AV-SQL's "generation dominates") --
    rep.append("\n### Real token breakdown by pipeline stage")
    stage_order = ["rewrite", "propose", "generate", "plan", "compose", "revise",
                   "semantic", "direct", "embed"]
    rep.append("| stage | " + " | ".join(labels.get(c, c) for c in order) + " |")
    rep.append("|---|" + "---|" * len(order))
    for st in stage_order:
        cells, any_nonzero = [], False
        for c in order:
            by = cfgs[c]["summary"].get("real_tokens_by_stage", {})
            tot = cfgs[c]["summary"]["real_total_tokens"] or 1
            t = by.get(st, {})
            tk = t.get("prompt", 0) + t.get("completion", 0)
            any_nonzero = any_nonzero or bool(tk)
            cells.append(f"{tk:,} ({100*tk/tot:.0f}%)")
        if any_nonzero:
            rep.append(f"| {st} | " + " | ".join(cells) + " |")

    rep.append(f"\n![gen curve]({os.path.basename(f1)})")
    rep.append(f"![token curve]({os.path.basename(f2)})")
    report_path = os.path.join(RESULTS_DIR, f"{args.tag}_{args.dataset}_report.md")
    open(report_path, "w").write("\n".join(rep))
    print("Wrote:", f1, f2, report_path)
    print("\n".join(rep))


if __name__ == "__main__":
    main()
