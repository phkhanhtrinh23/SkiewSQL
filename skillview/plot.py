"""Plot the SkillView-SQL learning curve: cumulative CTE generations & reuse rate."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from skillview.build_db import build, DB_DEFAULT
from skillview.run import run_config, RESULTS_DIR

db = build(DB_DEFAULT)
_, rows_a = run_config("A", use_memory=True, use_guard=True, fresh_db=db)
_, rows_b = run_config("B", use_memory=False, use_guard=True, fresh_db=db)

idx = list(range(1, len(rows_a) + 1))
cum_a = [r["cum_generated"] for r in rows_a]
cum_b = [r["cum_generated"] for r in rows_b]
reuse_a = [r["reused"] / r["n_wants"] for r in rows_a]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2))
ax1.plot(idx, cum_b, "o--", color="#c0392b", label="Baseline (AV-SQL, no memory)")
ax1.plot(idx, cum_a, "o-", color="#2471a3", label="SkillView (self-growing graph)")
ax1.fill_between(idx, cum_a, cum_b, color="#2471a3", alpha=0.08)
ax1.set_xlabel("question index (sequential)")
ax1.set_ylabel("cumulative CTE generations")
ax1.set_title("Regeneration avoided over a question stream")
ax1.legend(loc="upper left", fontsize=9)
ax1.grid(alpha=0.3)

ax2.bar(idx, reuse_a, color="#27ae60", alpha=0.85)
ax2.set_xlabel("question index (sequential)")
ax2.set_ylabel("view reuse rate (per question)")
ax2.set_title("SkillView reuse: cold-start builds -> warm reuse")
ax2.set_ylim(0, 1.05)
ax2.grid(alpha=0.3, axis="y")

fig.tight_layout()
out = os.path.join(RESULTS_DIR, "learning_curve.png")
os.makedirs(RESULTS_DIR, exist_ok=True)
fig.savefig(out, dpi=130)
print("saved", out)
