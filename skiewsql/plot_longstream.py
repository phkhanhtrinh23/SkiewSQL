"""plot_longstream.py — long-stream token dynamics: B (no memory) vs S-full (whole-registry injection) vs S-selective (top-k injection). Shows whether the per-question token cost of the seed config grows with the stream (whole-registry injection) or stays bounded (selective injection), relative to the flat baseline. Reads: results_real/runs/sqlite/spider/longfull_spider_B_Baseline_AVSQL.json results_real/runs/sqlite/spider/longfull_spider_S_ColdStart_Seed.json results_real/runs/sqlite/spider/longsel_spider_S_ColdStart_Seed.json Writes: results_real/runs/sqlite/spider/longstream_token_curve.png  and prints a stats table."""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skiewsql.paths import sqlite_run_dir

RD = str(sqlite_run_dir("spider"))

SERIES = [
    ("B · baseline (no memory)", "longfull_spider_B_Baseline_AVSQL.json", "#d62728"),
    ("S · seed, whole-registry inject", "longfull_spider_S_ColdStart_Seed.json", "#9467bd"),
    ("S · seed, top-k inject (fix)", "longsel_spider_S_ColdStart_Seed.json", "#1f77b4"),
]


def _rows(path):
    d = json.load(open(os.path.join(RD, path)))
    return sorted(d["rows"], key=lambda r: r["db_index"])


def _roll(xs, ys, w=5):
    out = []
    for i in range(len(ys)):
        lo = max(0, i - w + 1)
        out.append(sum(ys[lo:i + 1]) / (i + 1 - lo))
    return xs, out


def main():
    loaded = []
    for label, fname, color in SERIES:
        p = os.path.join(RD, fname)
        if not os.path.exists(p):
            print(f"missing: {fname}")
            continue
        loaded.append((label, _rows(fname), color))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))

    # left: per-question tokens (rolling mean) vs question index
    for label, rows, color in loaded:
        xs = [r["db_index"] for r in rows]
        ys = [r["tokens"] / 1000 for r in rows]
        rx, ry = _roll(xs, ys, 5)
        ax1.plot(xs, ys, ".", ms=4, alpha=0.25, color=color)
        ax1.plot(rx, ry, "-", lw=2, color=color, label=label)
    ax1.set_xlabel("question index within database (sequential stream)")
    ax1.set_ylabel("tokens per question (thousands, 5-pt rolling mean)")
    ax1.set_title("Per-question token cost vs stream position — world_1")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # right: cumulative tokens vs question index
    for label, rows, color in loaded:
        xs, cum, acc = [], [], 0
        for r in rows:
            acc += r["tokens"]
            xs.append(r["db_index"])
            cum.append(acc / 1000)
        ax2.plot(xs, cum, "-", lw=2, color=color, label=label)
    ax2.set_xlabel("question index within database (sequential stream)")
    ax2.set_ylabel("cumulative tokens (thousands)")
    ax2.set_title("Cumulative token cost — world_1")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    out = os.path.join(RD, "longstream_token_curve.png")
    plt.savefig(out, dpi=130)
    plt.close()

    # stats table + slope (early vs late per-question tokens)
    print(f"\n{'config':32} {'Q':>3} {'totTok':>9} {'tok/Q':>7} {'early10':>8} {'late10':>8} "
          f"{'gens':>5} {'reuse%':>7} {'acc%':>6}")
    for label, rows, _c in loaded:
        n = len(rows)
        tot = sum(r["tokens"] for r in rows)
        early = sum(r["tokens"] for r in rows[:10]) / min(10, n)
        late = sum(r["tokens"] for r in rows[-10:]) / min(10, n)
        gens = sum(r["generated"] for r in rows)
        reuse = sum(r["reused"] for r in rows)
        nviews = sum(r["n_views"] for r in rows) or 1
        acc = 100 * sum(r["correct"] for r in rows) / n
        print(f"{label:32} {n:>3} {tot:>9,} {tot//n:>7,} {early/1000:>7.1f}k {late/1000:>7.1f}k "
              f"{gens:>5} {100*reuse/nviews:>6.1f}% {acc:>5.1f}%")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
