#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
bench_root="$repo_root/skiewsql/results_real/benchmarks/architecture"
run_root="$bench_root/runs/current"
graph_root="$bench_root/graphs/current"
log_root="$bench_root/logs/current"

mkdir -p "$run_root" "$graph_root" "$log_root"
cd "$repo_root"

export SKIEW_LLM_PROVIDER=ollama
export SKIEW_OLLAMA_MODEL=gemma3:4b

common=(
  --limit 20
  --model local-gemma3-4b
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
  local tag="semantic20_${arm}"
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

run_arm av_nograph nx1 B
run_arm av_graph nx1 A
run_arm dependency_graph nxm A
run_arm adaptive_graph auto A

echo "BENCHMARK COMPLETE $(date --iso-8601=seconds)"
