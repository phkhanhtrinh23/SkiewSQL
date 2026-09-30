#!/usr/bin/env python3
"""Build the current four-arm architecture report from the raw per-question JSON files."""

from __future__ import annotations

import collections
import glob
import itertools
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "current"
REPORT = HERE / "REPORT.md"
SUMMARY = RUNS / "CURRENT_SUMMARY.json"

ARMS = collections.OrderedDict([
    ("av_nograph", "AV-SQL, no graph"),
    ("av_graph", "AV-SQL + graph"),
    ("dependency_graph", "Dependency N×M + graph"),
    ("adaptive_graph", "Adaptive + graph"),
])
DATASETS = collections.OrderedDict([
    ("spider", "Spider"),
    ("bird", "BIRD"),
    ("spider2lite", "Spider2-lite"),
])


def load(arm: str, dataset: str) -> dict:
    pattern = str(RUNS / f"semantic20_{arm}_{dataset}_*.json")
    paths = [Path(p) for p in glob.glob(pattern) if not p.endswith("_summary.json")]
    if len(paths) != 1:
        raise RuntimeError(f"expected one raw file for {arm}/{dataset}, got {paths}")
    return json.loads(paths[0].read_text())


def pct(n: int | float, d: int | float) -> str:
    return f"{100 * n / d:.1f}%" if d else "n/a"


def integer(n: int | float) -> str:
    return f"{int(n):,}"


def stage_totals(data: dict[str, dict[str, dict]]) -> dict:
    totals = {}
    for arm in ARMS:
        stages = collections.defaultdict(lambda: {"tokens": 0, "calls": 0})
        for dataset in DATASETS:
            for tag, value in data[arm][dataset]["summary"]["real_tokens_by_stage"].items():
                stages[tag]["tokens"] += value["prompt"] + value["completion"]
                stages[tag]["calls"] += value["calls"]
        totals[arm] = dict(stages)
    return totals


def main() -> None:
    data = {arm: {dataset: load(arm, dataset) for dataset in DATASETS} for arm in ARMS}
    overall = {}
    for arm in ARMS:
        rows = list(itertools.chain.from_iterable(data[arm][ds]["rows"] for ds in DATASETS))
        summaries = [data[arm][ds]["summary"] for ds in DATASETS]
        overall[arm] = {
            "correct": sum(bool(r["correct"]) for r in rows),
            "questions": len(rows),
            "tokens": sum(s["real_total_tokens"] for s in summaries),
            "calls": sum(sum(v["calls"] for v in s["real_tokens_by_stage"].values()) for s in summaries),
            "generated": sum(s["total_views_generated"] for s in summaries),
            "reuse_questions": sum(s["n_reuse_fired"] for s in summaries),
            "negative_reuse": sum(s["negative_reuse_count"] for s in summaries),
            "negative_reuse_raw": sum(s["negative_reuse_raw_count"] for s in summaries),
            "measured_seconds": round(sum(r["secs"] for r in rows), 2),
            "routes": dict(collections.Counter(r["architecture_route"] for r in rows)),
            "saved_graph_views": (None if arm == "av_nograph" else
                                  sum(sum(s["final_graph_sizes"].values()) for s in summaries)),
        }

    pairwise = {}
    adaptive = "adaptive_graph"
    for other in ("av_nograph", "av_graph", "dependency_graph"):
        pairwise[other] = {}
        for dataset in DATASETS:
            aa = {r["qid"]: r for r in data[adaptive][dataset]["rows"]}
            bb = {r["qid"]: r for r in data[other][dataset]["rows"]}
            wins = [qid for qid in aa if aa[qid]["correct"] and not bb[qid]["correct"]]
            losses = [qid for qid in aa if not aa[qid]["correct"] and bb[qid]["correct"]]
            pairwise[other][dataset] = {
                "wins": wins,
                "losses": losses,
                "ties": len(aa) - len(wins) - len(losses),
            }

    routes = {}
    for dataset in DATASETS:
        by_route = collections.defaultdict(list)
        for row in data[adaptive][dataset]["rows"]:
            by_route[row["architecture_route"]].append(row)
        routes[dataset] = {}
        for route, rows in sorted(by_route.items()):
            routes[dataset][route] = {
                "questions": len(rows),
                "correct": sum(bool(r["correct"]) for r in rows),
                "generated": sum(r["generated"] for r in rows),
                "reuse_questions": sum(bool(r["used_reuse"]) for r in rows),
                "negative_reuse": sum(bool(r["negative_reuse"]) for r in rows),
                "tokens": sum(r["tokens"] for r in rows),
            }

    serializable = {
        "scope": {
            "questions": 60,
            "runs": 240,
            "model": "Ollama gemma3:4b, temperature 0",
            "datasets": {
                "spider": "20 from student_transcripts_tracking",
                "bird": "20 from european_football_2",
                "spider2lite": "15 bank_sales_trading + 5 education_business",
            },
        },
        "overall": overall,
        "adaptive_routes": routes,
        "adaptive_pairwise": pairwise,
        "stages": stage_totals(data),
    }
    SUMMARY.write_text(json.dumps(serializable, indent=2) + "\n")

    lines = [
        "# Current architecture benchmark: semantic adaptive routing",
        "",
        "> Fresh run on 30 September 2026. This is the active report. The retired focused-holistic "
        "arm is deliberately excluded from the interface, run set, and comparison tables.",
        "",
        "## Bottom line",
        "",
        "Adaptive is **not universally more accurate** in this sample. It ties AV-SQL without a "
        "graph overall at **20/60 (33.3%)**, while using **22.2% fewer tokens** and generating "
        "**19 instead of 106 CTEs**. The tie hides a strong dataset interaction: adaptive gains "
        "four answers on Spider and loses four on BIRD. All four methods fail all 20 selected "
        "Spider2-lite questions.",
        "",
        "The good news is that semantic routing works very well on the selected Spider stream: "
        "adaptive reaches **17/20 (85%)**, compared with 13/20 for AV-SQL without graph, while "
        "using 78.0% fewer tokens. The bad news is that moderate BIRD questions still enter "
        "aggressive AV graph reuse, producing 13 non-trivial negative-reuse failures.",
        "",
        "## Experimental setup",
        "",
        "- Spider: first 20 questions from `student_transcripts_tracking`.",
        "- BIRD: first 20 questions from `european_football_2`.",
        "- Spider2-lite: all 15 `bank_sales_trading` plus all 5 `education_business` questions.",
        "- Model: local Ollama `gemma3:4b`, temperature 0.",
        "- Common settings: 1,000-token schema chunks, maximum 3 subgoals, 1 view-validation "
        "attempt, 1 SQL repair, 1 self-consistency pass, no value linking, retrieval threshold 0.6.",
        "- Each graph-enabled dataset run starts with an empty graph and grows it sequentially "
        "question by question. Graphs are not shared between architectures or datasets.",
        "- `N` is the number of schema chunks and `M` is the number of dependency subgoals. "
        "Dependency mode aligns every one of the `M` subgoals against all `N` chunks.",
        "",
        "## Accuracy by dataset",
        "",
        "| Method | Spider | BIRD | Spider2-lite | Overall |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm, label in ARMS.items():
        vals = []
        for dataset in DATASETS:
            rows = data[arm][dataset]["rows"]
            correct = sum(bool(r["correct"]) for r in rows)
            vals.append(f"{correct}/20 ({pct(correct, 20)})")
        o = overall[arm]
        lines.append(f"| {label} | {' | '.join(vals)} | {o['correct']}/60 ({pct(o['correct'], 60)}) |")

    lines += [
        "",
        "## Pooled cost, graph, and reuse results",
        "",
        "`Measured time` is the sum of per-question pipeline timers in the result rows. It excludes "
        "dataset preparation and model loading. The Spider2-lite AV-graph run also had one "
        "240-second question timeout, which is recorded separately and is not represented faithfully "
        "by that row timer.",
        "",
        "| Method | Correct | Tokens | LLM/embed calls | CTEs generated | Questions with reuse | Negative reuse | Saved graph views | Measured time |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, label in ARMS.items():
        o = overall[arm]
        graph = "n/a" if o["saved_graph_views"] is None else integer(o["saved_graph_views"])
        lines.append(
            f"| {label} | {o['correct']}/60 | {integer(o['tokens'])} | {integer(o['calls'])} | "
            f"{integer(o['generated'])} | {o['reuse_questions']}/60 | {o['negative_reuse']} "
            f"({o['negative_reuse_raw']} raw) | {graph} | {o['measured_seconds']:.2f}s |"
        )

    lines += [
        "",
        "Relative to AV-SQL without graph:",
        "",
        "- AV-SQL + graph saves 27.1% of tokens and 90.6% of CTE generation, but loses 6 correct "
        "answers and incurs 33 non-trivial negative reuses.",
        "- Dependency N×M also scores 14/60, uses 31.0% more tokens, and nearly doubles calls. "
        "Alignment alone accounts for 532,996 tokens and 384 calls.",
        "- Adaptive preserves the same 20/60 accuracy, saves 22.2% of tokens and 82.1% of CTE "
        "generation, but makes 24.3% more calls because classification and alignment add many short calls.",
        "",
        "## Detailed dataset metrics",
        "",
        "| Dataset | Method | Correct | Tokens | Calls | Generated | Reuse-hit questions | Non-trivial negative reuse | Mean seconds/question |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset, dataset_label in DATASETS.items():
        for arm, arm_label in ARMS.items():
            d = data[arm][dataset]
            s, rows = d["summary"], d["rows"]
            correct = sum(bool(r["correct"]) for r in rows)
            calls = sum(v["calls"] for v in s["real_tokens_by_stage"].values())
            lines.append(
                f"| {dataset_label} | {arm_label} | {correct}/20 | {integer(s['real_total_tokens'])} | "
                f"{calls} | {s['total_views_generated']} | {s['n_reuse_fired']} | "
                f"{s['negative_reuse_count']} | {s['avg_secs_per_q']:.2f} |"
            )

    lines += [
        "",
        "## What adaptive actually selected",
        "",
        "| Dataset | Route | Questions | Correct | Generated CTEs | Reuse-hit questions | Negative reuse | Tokens |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    route_labels = {
        "direct_sql": "Easy → direct SQL",
        "av_nx1_graph": "Moderate → AV N×1 + graph",
        "dependency_nxm_graph": "Hard → dependency N×M + graph",
    }
    for dataset, dataset_label in DATASETS.items():
        for route, rr in routes[dataset].items():
            lines.append(
                f"| {dataset_label} | {route_labels.get(route, route)} | {rr['questions']} | "
                f"{rr['correct']} ({pct(rr['correct'], rr['questions'])}) | {rr['generated']} | "
                f"{rr['reuse_questions']} | {rr['negative_reuse']} | {integer(rr['tokens'])} |"
            )

    lines += [
        "",
        "Interpretation:",
        "",
        "- Spider benefited because 18/20 questions bypassed views and graph retrieval. Direct SQL "
        "was correct on 15/18, and both moderate questions were correct.",
        "- BIRD routed 17/20 questions to moderate AV+graph. Reusing two early views broadly over "
        "the stream saved cost but caused 13 negative-reuse failures. No question was classified hard.",
        "- Spider2-lite routed 16/20 questions to hard N×M and 4/20 to moderate AV. This routing "
        "looks structurally plausible, but the local 4B model produced no correct final answers.",
        "",
        "## Paired adaptive wins and losses",
        "",
        "A win means adaptive is correct and the compared method is wrong on the same question. A "
        "loss is the reverse. A tie includes both-correct and both-wrong cases.",
        "",
        "| Compared with | Spider W/L/T | BIRD W/L/T | Spider2-lite W/L/T | Overall W/L/T |",
        "|---|---:|---:|---:|---:|",
    ]
    for other in ("av_nograph", "av_graph", "dependency_graph"):
        counts = []
        tw = tl = tt = 0
        for dataset in DATASETS:
            p = pairwise[other][dataset]
            w, l, t = len(p["wins"]), len(p["losses"]), p["ties"]
            counts.append(f"{w}/{l}/{t}")
            tw, tl, tt = tw + w, tl + l, tt + t
        lines.append(f"| {ARMS[other]} | {' | '.join(counts)} | {tw}/{tl}/{tt} |")

    lines += [
        "",
        "The most important paired comparison is adaptive versus AV-SQL without graph:",
        "",
        "- Adaptive Spider wins: `spider_dev_509`, `spider_dev_510`, `spider_dev_513`, "
        "`spider_dev_519`, `spider_dev_520`.",
        "- Adaptive Spider loss: `spider_dev_517`.",
        "- Adaptive BIRD losses: `bird_dev_1020`, `bird_dev_1036`, `bird_dev_1038`, "
        "`bird_dev_1039`.",
        "- Spider2-lite has 20 both-wrong ties. Overall this is 5 wins, 5 losses, and 50 ties.",
        "",
        "## Token/call breakdown by stage",
        "",
        "| Method | Stage | Tokens | Calls |",
        "|---|---|---:|---:|",
    ]
    stages = stage_totals(data)
    for arm, arm_label in ARMS.items():
        for stage, values in sorted(stages[arm].items(), key=lambda item: -item[1]["tokens"]):
            lines.append(f"| {arm_label} | `{stage}` | {integer(values['tokens'])} | {values['calls']} |")

    lines += [
        "",
        "## Conclusions",
        "",
        "1. **Keep adaptive as the research direction, but do not claim a universal accuracy win.** "
        "This run supports an efficiency claim at equal pooled accuracy and a strong Spider result.",
        "2. **Do not enable aggressive graph reuse by default for moderate questions yet.** BIRD's "
        "high reuse rate is mostly harmful. Compatibility needs stronger grain/filter/output checks "
        "or a verifier before a saved view can replace fresh AV generation.",
        "3. **Easy-question bypass is the clearest success.** It removes unnecessary views, graph "
        "lookups, and planner calls while improving Spider accuracy.",
        "4. **Dependency N×M needs cheaper alignment.** It is safer than broad AV reuse here, but its "
        "384 alignment calls and 532,996 alignment tokens do not produce an accuracy gain.",
        "5. **Spider2-lite remains unresolved.** Because all methods score zero, this subset cannot "
        "distinguish architectures with the current local model. A stronger model and error-focused "
        "prompt/schema debugging are required before drawing architectural conclusions from it.",
        "",
        "## Reproduction and artifacts",
        "",
        "Run all four arms with:",
        "",
        "```bash",
        "bash skiewsql/results_real/benchmarks/architecture/run_current_benchmark.sh",
        "python skiewsql/results_real/benchmarks/architecture/analyze_current_benchmark.py",
        "```",
        "",
        "Raw per-question outputs and the machine-readable aggregate are under `runs/current/`. "
        "grown graphs are under `graphs/current/`. Per-process logs are under `logs/current/`.",
        "",
        "## Validity limits",
        "",
        "This is a controlled architecture test, not a publication-grade benchmark: each named "
        "dataset sample covers only one or two databases, uses a small local model, and contains 20 "
        "questions. Results may also vary across local inference runs despite temperature 0. The next "
        "confirmation should cover more database domains and use a stronger fixed model.",
        "",
    ]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
