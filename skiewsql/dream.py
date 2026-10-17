"""dream.py — offline library **consolidation** ("dreaming"). Between runs, consume the grown registry's accumulated evidence — each view's `validated_on` (questions it answered correctly on reuse) and `counter_examples` (questions where reusing it was a bad hit) — to produce a *cleaner* seed library:

  1. **Re-derive contracts** — recompute Φ/G from each view's SQL (`sqlview.enforce_contract`) so the compatibility guard and the dedup signature are accurate.
  2. **Prune harmful views** — drop any view that is net-negative (more `counter_examples` than `validated_on`, and at least `min_counter` bad hits): these are the direct source of negative reuse, removed at the source rather than re-rejected every query.
  3. **Merge near-duplicates** — views with the same structural signature (category, outputs, grain, Φ) collapse to one (keep the more-validated. Union the evidence. Redirect DEPENDS_ON), shrinking the retrieval space so there are fewer near-identical candidates to confuse the selector.

The dreamed registry is saved as a fresh seed library. Feed it back via `realrun --configs S --seed_dir <dreamed>`. This is the memory-consolidation analogue of experience replay: the library self-cleans using what past questions taught it."""
from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Dict, List, Tuple

from skiewsql import sqlview
from skiewsql.core import SkillRegistry, ViewSpec
from skiewsql.coldstart import _signature
from skiewsql.paths import SEED_REGISTRIES_DIR

SEED_ROOT = str(SEED_REGISTRIES_DIR)


def dream_registry(registry: SkillRegistry, dialect: str = "sqlite", min_counter: int = 2) -> Tuple[SkillRegistry, Dict]:
    report = {"n_before": registry.n_views(), "reconstructed_contract": 0, "pruned": [], "merged": []}

    # 1. re-derive accurate Φ/G from the SQL body
    for v in registry.views.values():
        before = (tuple(v.grain or []), tuple(sorted((v.semantic_filters or {}).items())))
        sqlview.enforce_contract(v, dialect)
        after = (tuple(v.grain or []), tuple(sorted((v.semantic_filters or {}).items())))
        if before != after:
            report["reconstructed_contract"] += 1

    # 2a. prune trivial single-table projections — reusing them is a no-op (semantically identical to querying the base table), so they save no generation work but soak up reuse blame + candidate slots. Dropping them from the library is free: any query that needs one regenerates it trivially.
    report["pruned_trivial"] = []
    for name in list(registry.views):
        if sqlview.is_trivial_projection(registry.views[name]):
            # keep it only if another surviving view depends on it (it's a real building block)
            if any(name in (w.depends_on or []) for w in registry.views.values() if w.name != name):
                continue
            registry.remove_view(name)
            report["pruned_trivial"].append(name)

    # 2b. prune harmful views (net-negative on the evidence)
    for name in list(registry.views):
        v = registry.views[name]
        nc, nv = len(v.counter_examples or []), len(v.validated_on or [])
        if nc >= min_counter and nc > nv:
            registry.remove_view(name)
            report["pruned"].append({"name": name, "counter": nc, "validated": nv})

    # 3. merge near-duplicates by structural signature
    by_sig: Dict[tuple, str] = {}
    for name in list(registry.views):
        v = registry.views.get(name)
        if v is None:
            continue
        sig = _signature(v)
        if sig not in by_sig:
            by_sig[sig] = name
            continue
        keep = by_sig[sig]
        # keep the more-validated view. Drop the other
        if len(v.validated_on or []) > len(registry.views[keep].validated_on or []):
            keep, drop = name, keep
        else:
            drop = name
        kv, dv = registry.views[keep], registry.views[drop]
        kv.validated_on = list({*(kv.validated_on or []), *(dv.validated_on or [])})[:10]
        kv.counter_examples = list({*(kv.counter_examples or []), *(dv.counter_examples or [])})[:10]
        # redirect any view that depended on `drop` to `keep`
        for w in registry.views.values():
            if drop in (w.depends_on or []):
                w.depends_on = [keep if d == drop else d for d in w.depends_on]
        registry.remove_view(drop)
        by_sig[sig] = keep
        report["merged"].append({"kept": keep, "dropped": drop})

    report["n_after"] = registry.n_views()
    return registry, report


def main():
    ap = argparse.ArgumentParser(description="Dream: consolidate grown registries into a cleaner seed library.")
    ap.add_argument("--grown_dir", required=True, help="dir of grown {db}.json registries (from a config-S/A run)")
    ap.add_argument("--out_tag", required=True,
                    help="output seed tag -> results_real/registries/seed/<out_tag>/")
    ap.add_argument("--dialect", default="sqlite", choices=["sqlite", "snowflake", "bigquery"])
    ap.add_argument("--min_counter", type=int, default=2)
    args = ap.parse_args()

    out_dir = os.path.join(SEED_ROOT, args.out_tag)
    os.makedirs(out_dir, exist_ok=True)
    files = [f for f in glob.glob(os.path.join(args.grown_dir, "*.json"))
             if "report" not in f and "summary" not in f]
    print(f"Dreaming {len(files)} grown registries from {args.grown_dir}\n")
    tot = {"before": 0, "after": 0, "trivial": 0, "pruned": 0, "merged": 0, "contract": 0}
    for f in sorted(files):
        db = os.path.basename(f)[:-5]
        registry = sqlview.load_registry(f)
        registry, rep = dream_registry(registry, dialect=args.dialect, min_counter=args.min_counter)
        sqlview.save_registry(registry, os.path.join(out_dir, f"{db}.json"))
        json.dump(rep, open(os.path.join(out_dir, f"{db}.dream.json"), "w"), indent=2)
        tot["before"] += rep["n_before"]; tot["after"] += rep["n_after"]
        tot["trivial"] += len(rep.get("pruned_trivial", []))
        tot["pruned"] += len(rep["pruned"]); tot["merged"] += len(rep["merged"])
        tot["contract"] += rep["reconstructed_contract"]
        print(f"  [{db}] {rep['n_before']}->{rep['n_after']} views | trivial {len(rep.get('pruned_trivial', []))} "
              f"| pruned {len(rep['pruned'])} harmful | merged {len(rep['merged'])} dups "
              f"| contracts fixed {rep['reconstructed_contract']}")
    print(f"\nTotal: {tot['before']}->{tot['after']} views | trivial-pruned {tot['trivial']} | "
          f"harmful-pruned {tot['pruned']} | merged {tot['merged']} | contracts fixed {tot['contract']}  ->  {out_dir}")


if __name__ == "__main__":
    main()
