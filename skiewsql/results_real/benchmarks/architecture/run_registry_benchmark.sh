#!/usr/bin/env bash
# Skill-registry rerun of the semantic20 architecture benchmark: same models, datasets, and settings as
# run_current_benchmark.sh, but realrun.py now defaults to the skill registry (--skill_registry 1).
# Outputs go to runs/registry, graphs/registry, logs/registry so the semantic20 artifacts stay untouched.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
bench_root="$repo_root/skiewsql/results_real/benchmarks/architecture"
# OUT selects the output subdirectory and RUN_NAME the tag prefix, so reruns never overwrite earlier ones.
out="${OUT:-registry}"
run_name="${RUN_NAME:-registry20}"
run_root="$bench_root/runs/$out"
graph_root="$bench_root/graphs/$out"
log_root="$bench_root/logs/$out"

mkdir -p "$run_root" "$graph_root" "$log_root"
cd "$repo_root"

# PROVIDER / MODEL override the default local model (e.g. PROVIDER=openai MODEL=gpt-5-mini).
export SKIEW_LLM_PROVIDER="${PROVIDER:-ollama}"
export SKIEW_OLLAMA_MODEL=gemma3:4b

common=(
  --limit "${LIMIT:-20}"
  --model "${MODEL:-local-gemma3-4b}"
  --chunk_budget 1000
  --max_subgoals 3
  --repair 1
  --view_attempts 1
  --self_consistency 1
  --no_valuelink
  --results_dir "$run_root"
  --grown_root "$graph_root"
)

run_one() {
  local arm="$1"
  local architecture="$2"
  local config="$3"
  local dataset="$4"
  local dbs="$5"
  local tag="${run_name}_${arm}"
  local logfile="$log_root/${tag}_${dataset}.log"

  echo "START arm=$arm dataset=$dataset dbs=$dbs $(date --iso-8601=seconds)"
  python -m skiewsql.realrun \
    --dataset "$dataset" \
    --dbs "$dbs" \
    --architecture "$architecture" \
    --configs "$config" \
    --tag "$tag" \
    "${common[@]}" 2>&1 | tee "$logfile"
  echo "DONE arm=$arm dataset=$dataset $(date --iso-8601=seconds)"
}

run_arm() {
  local arm="$1"
  local architecture="$2"
  local config="$3"
  run_one "$arm" "$architecture" "$config" spider student_transcripts_tracking
  run_one "$arm" "$architecture" "$config" bird european_football_2
  run_one "$arm" "$architecture" "$config" spider2lite bank_sales_trading,education_business
}

# ARMS selects which arms to run (default both), so arms can run as parallel processes.
for arm in ${ARMS:-av_nograph adaptive_graph}; do
  case "$arm" in
    av_nograph) run_arm av_nograph nx1 B ;;
    adaptive_graph) run_arm adaptive_graph auto A ;;
  esac
done

echo "BENCHMARK COMPLETE $(date --iso-8601=seconds)"
