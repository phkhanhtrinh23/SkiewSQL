#!/usr/bin/env python3
"""Compare the skill-registry rerun (runs/registry, tag registry20_*) with the earlier semantic20 runs (runs/current) for the AV-SQL no-graph and adaptive arms. Prints Markdown tables and writes REGISTRY_SUMMARY.json."""

from __future__ import annotations

import collections
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = {"before": (HERE / "runs" / "current", "semantic20"), "registry": (HERE / "runs" / "registry", "registry20"),
        "fixed": (HERE / "runs" / "registry_fix", "registryfix20"),
        "gpt5mini": (HERE / "runs" / "registry_gpt5mini", "gpt5mini20"),
        "gpt5full": (HERE / "runs" / "registry_gpt5mini_full", "gpt5minifull")}
ARMS = collections.OrderedDict([("av_nograph", "AV-SQL, no graph"), ("adaptive_graph", "Adaptive + graph")])
DATASETS = collections.OrderedDict([("spider", "Spider"), ("bird", "BIRD"), ("spider2lite", "Spider2-lite")])
LEARNING_TAGS = {"ablation_generate", "ablation_av_view", "gen_tests", "promote_describe", "extract_final"}


def load(run: str, arm: str, dataset: str) -> dict | None:
    root, tag = RUNS[run]
    paths = [p for p in glob.glob(str(root / f"{tag}_{arm}_{dataset}_*.json")) if not p.endswith("_summary.json")]
    return json.loads(Path(paths[0]).read_text()) if len(paths) == 1 else None


def _half(rows, r) -> int:
    return sum(1 for x in rows if x["db_id"] == r["db_id"]) // 2


def stats(d: dict) -> dict:
    rows, s = d["rows"], d["summary"]
    stages = s.get("real_tokens_by_stage", {})
    calls = sum(v["calls"] for v in stages.values())
    learn_tok = sum(v["prompt"] + v["completion"] for k, v in stages.items() if k in LEARNING_TAGS)
    learn_calls = sum(v["calls"] for k, v in stages.items() if k in LEARNING_TAGS)
    return {
        "n": len(rows), "correct": sum(bool(r["correct"]) for r in rows),
        "tokens": s["real_total_tokens"], "calls": calls,
        "learn_tokens": learn_tok, "learn_calls": learn_calls,
        "generated": sum(r["generated"] for r in rows),
        "reuse_q": sum(bool(r.get("used_reuse")) for r in rows),
        "neg_reuse": sum(bool(r.get("negative_reuse")) for r in rows),
        "neg_reuse_referenced": sum(bool(r.get("negative_reuse_referenced")) for r in rows),
        "reuse_executed": sum(len(r.get("reuse_executed", [])) for r in rows),
        "causal_pos": sum(bool(r.get("causal_positive_reuse")) for r in rows),
        "causal_neg": sum(bool(r.get("causal_negative_reuse")) for r in rows),
        "align_calls": sum(r.get("alignment_calls", 0) or 0 for r in rows),
        "prefetch_hits": sum(r.get("prefetch_hits", 0) for r in rows),
        "prefetch_ungrounded": sum(r.get("prefetch_ungrounded", 0) for r in rows),
        "admitted": sum(sum(1 for o in (r.get("admitted") or {}).values() if str(o).startswith("admitted"))
                        for r in rows),
        "verify_reject": sum(r.get("verify_reject", 0) for r in rows),
        "errors": sum(1 for r in rows if r.get("architecture_route") == "failed"),
        "learn_errors": sum(1 for r in rows if r.get("learn_error")),
        "graph": s.get("final_graph_sizes", {}),
        "routes": collections.Counter(r.get("architecture_route", "?") for r in rows),
        "secs": sum(r.get("secs", 0) for r in rows),
        "by_qid": {r["qid"]: bool(r["correct"]) for r in rows},
        # does reuse grow as the registry fills? executed reuses in the first vs second half of each DB stream
        "reuse_first_half": sum(len(r.get("reuse_executed", [])) for r in rows
                                if r.get("db_index", 0) < _half(rows, r)),
        "reuse_second_half": sum(len(r.get("reuse_executed", [])) for r in rows
                                 if r.get("db_index", 0) >= _half(rows, r)),
        "reuse_q_second_half": sum(bool(r.get("reused")) for r in rows if r.get("db_index", 0) >= _half(rows, r)),
        "stages": stages,
    }


def paired(a: dict, b: dict) -> tuple[int, int, int, list, list]:
    wins = [q for q in a if a[q] and not b.get(q)]
    losses = [q for q in a if not a[q] and b.get(q)]
    return len(wins), len(losses), len(a) - len(wins) - len(losses), wins, losses


def main() -> None:
    S = {run: {arm: {ds: (stats(d) if (d := load(run, arm, ds)) else None) for ds in DATASETS}
               for arm in ARMS} for run in RUNS}
    out = []
    out.append("## Accuracy\n")
    out.append("| Method | Run | " + " | ".join(DATASETS.values()) + " | Overall |")
    out.append("|---|---|" + "---:|" * (len(DATASETS) + 1))
    for arm, label in ARMS.items():
        for run in RUNS:
            cells, c, n = [], 0, 0
            for ds in DATASETS:
                st = S[run][arm][ds]
                cells.append(f"{st['correct']}/{st['n']}" if st else "—")
                if st:
                    c, n = c + st["correct"], n + st["n"]
            if n:
                out.append(f"| {label} | {run} | " + " | ".join(cells) + f" | {c}/{n} |")
    out.append("\n## Cost and reuse per dataset\n")
    out.append("| Dataset | Method | Run | Correct | Tokens (learning) | Calls (learning) | CTEs generated | "
               "Reuse questions | Neg. reuse (old def / referenced) | Executed reuses | Causal +/− | "
               "Align calls | Prefetch hits (ungrounded) | Admitted | Verifier rejects | Graph |")
    out.append("|---|---|---|" + "---:|" * 13)
    for ds, dl in DATASETS.items():
        for arm, al in ARMS.items():
            for run in RUNS:
                st = S[run][arm][ds]
                if not st:
                    continue
                out.append(
                    f"| {dl} | {al} | {run} | {st['correct']}/{st['n']} | {st['tokens']:,} ({st['learn_tokens']:,}) | "
                    f"{st['calls']} ({st['learn_calls']}) | {st['generated']} | {st['reuse_q']} | "
                    f"{st['neg_reuse']} / {st['neg_reuse_referenced']} | {st['reuse_executed']} | "
                    f"{st['causal_pos']}/{st['causal_neg']} | {st['align_calls']} | {st['prefetch_hits']} ({st['prefetch_ungrounded']}) | "
                    f"{st['admitted']} | {st['verify_reject']} | {sum(st['graph'].values()) if st['graph'] else 0} |")
    out.append("\n## Reuse over the stream (adaptive: executed reuses, first half / second half of each DB)\n")
    for run in RUNS:
        cells = [f"{dl} {st['reuse_first_half']}/{st['reuse_second_half']}"
                 for ds, dl in DATASETS.items() if (st := S[run]["adaptive_graph"][ds])]
        if cells:
            out.append(f"- {run}: " + ", ".join(cells))
    out.append("\n## Routes (adaptive)\n")
    for run in RUNS:
        for ds, dl in DATASETS.items():
            st = S[run]["adaptive_graph"][ds]
            if st:
                out.append(f"- {run} {dl}: " + ", ".join(f"{k} {v}" for k, v in sorted(st["routes"].items())))
    out.append("\n## Paired comparisons (W/L/T, wins listed)\n")
    pairs = [("gpt5full adaptive vs gpt5full no-graph", ("gpt5full", "adaptive_graph"), ("gpt5full", "av_nograph")),
             ("gpt5mini adaptive vs gpt5mini no-graph", ("gpt5mini", "adaptive_graph"), ("gpt5mini", "av_nograph")),
             ("gpt5mini adaptive vs fixed (gemma) adaptive", ("gpt5mini", "adaptive_graph"), ("fixed", "adaptive_graph")),
             ("fixed adaptive vs registry adaptive", ("fixed", "adaptive_graph"), ("registry", "adaptive_graph")),
             ("fixed adaptive vs before adaptive", ("fixed", "adaptive_graph"), ("before", "adaptive_graph")),
             ("fixed adaptive vs fixed no-graph", ("fixed", "adaptive_graph"), ("fixed", "av_nograph")),
             ("fixed no-graph vs registry no-graph", ("fixed", "av_nograph"), ("registry", "av_nograph")),
             ("registry adaptive vs before adaptive", ("registry", "adaptive_graph"), ("before", "adaptive_graph")),
             ("registry adaptive vs registry no-graph", ("registry", "adaptive_graph"), ("registry", "av_nograph")),
             ("registry no-graph vs before no-graph", ("registry", "av_nograph"), ("before", "av_nograph"))]
    for label, (ra, aa), (rb, ab) in pairs:
        cells = []
        for ds, dl in DATASETS.items():
            a, b = S[ra][aa][ds], S[rb][ab][ds]
            if a and b:
                w, l, t, wins, losses = paired(a["by_qid"], b["by_qid"])
                cells.append(f"{dl} {w}/{l}/{t} (wins {wins or '—'}, losses {losses or '—'})")
        out.append(f"- **{label}**: " + "; ".join(cells))
    last = [r for r in RUNS if any(S[r]["adaptive_graph"][ds] for ds in DATASETS)][-1]
    out.append(f"\n## Stage breakdown, adaptive `{last}` run (tokens / calls, all datasets)\n")
    agg = collections.defaultdict(lambda: [0, 0])
    for ds in DATASETS:
        st = S[last]["adaptive_graph"][ds]
        for k, v in (st["stages"] if st else {}).items():
            agg[k][0] += v["prompt"] + v["completion"]
            agg[k][1] += v["calls"]
    out.append("| Stage | Tokens | Calls |\n|---|---:|---:|")
    for k, (t, c) in sorted(agg.items(), key=lambda x: -x[1][0]):
        out.append(f"| `{k}` | {t:,} | {c} |")
    print("\n".join(out))
    json.dump({run: {arm: {ds: ({k: v for k, v in st.items() if k not in ("by_qid", "stages", "routes")} | {
        "routes": dict(st["routes"])} if st else None) for ds, st in dss.items()} for arm, dss in arms.items()}
               for run, arms in S.items()},
              open(RUNS[last][0] / "REGISTRY_SUMMARY.json", "w"), indent=2)


if __name__ == "__main__":
    main()
