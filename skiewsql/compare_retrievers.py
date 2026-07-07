"""
compare_retrievers.py — dense vs hybrid(RRF: dense+BM25) retrieval, config S, world_1 40-Q stream.

Reports the outcome metrics (reuse, accuracy, tokens) AND the intrinsic retrieval metrics that
are not confounded by LLM nondeterminism: how many retrievals had >1 compatible candidate (where
fusion CAN act) and how often fusion OVERTURNED the dense top-1 pick.
"""
from __future__ import annotations

import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(_ROOT, "skiewsql", "results_real")


def load(tag):
    p = os.path.join(RD, f"{tag}_spider_S_ColdStart_Seed.json")
    return json.load(open(p)) if os.path.exists(p) else None


def diag_stats(rows):
    hits = multi = overturned = total = 0
    for r in rows:
        for entry in r.get("diag", []):
            for _name, d in entry.items():
                total += 1
                if d.get("hit"):
                    hits += 1
                    if d.get("rank") != "single" and "overturned_dense" in d:
                        multi += 1
                        if d.get("overturned_dense"):
                            overturned += 1
    return total, hits, multi, overturned


def summ(tag):
    d = load(tag)
    if not d:
        print(f"[{tag}] missing")
        return
    s, rows = d["summary"], d["rows"]
    n = len(rows)
    tot = s["real_total_tokens"]
    total, hits, multi, overturned = diag_stats(rows)
    print(f"\n== {tag} ({s['config']}) ==")
    print(f"  questions            {n}")
    print(f"  exec accuracy        {100*s['exec_accuracy']:.1f}%")
    print(f"  exact reuse rate     {100*s['exact_reuse_rate']:.1f}%   (seed {100*s['seed_reuse_rate']:.1f}%)")
    print(f"  total CTE gens       {s['total_views_generated']}")
    print(f"  real total tokens    {tot:,}  ({tot//n:,}/Q)")
    print(f"  retrieval calls      {total}  |  hits {hits}  |  multi-candidate {multi}  |  fusion-overturned {overturned}")


if __name__ == "__main__":
    print("Dense vs Hybrid retriever — config S, world_1 (40 Q), gen_topk=6")
    summ("rdense")
    summ("rhybrid")
    print("\nNote: 'multi-candidate' = retrievals where >1 view passed the contract (only there can")
    print("fusion act); 'fusion-overturned' = hybrid chose a different view than dense top-1.")
