#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

MODE="${MODE:-smoke}"
PYTHON_BIN="${PYTHON_BIN:-python}"

run_tests() {
  "$PYTHON_BIN" -m pytest -q
}

run_local_demo() {
  "$PYTHON_BIN" -m skiewsql.run
}

run_dataset() {
  local dataset="$1"
  "$PYTHON_BIN" -m skiewsql.realrun \
    --dataset "$dataset" \
    --dbs "${DBS:-top:4}" \
    --limit "${LIMIT:-30}" \
    --model "${MODEL:-gpt-5-mini}" \
    --architecture "${ARCHITECTURE:-nx1}" \
    --skill_registry 1 \
    --configs "${CONFIGS:-A}" \
    --tag "${TAG:-paper}"
}

check_credentials() {
  local provider="${SKIEW_LLM_PROVIDER:-openai}"
  local embed_default="openai"
  case "$provider" in
    openai) : "${OPENAI_API_KEY:?Set OPENAI_API_KEY}" ;;
    together) : "${TOGETHER_API_KEY:?Set TOGETHER_API_KEY}" ;;
    openrouter) : "${OPENROUTER_API_KEY:?Set OPENROUTER_API_KEY}" ;;
    ollama) embed_default="ollama" ;;
    *) echo "Unsupported SKIEW_LLM_PROVIDER=$provider" >&2; exit 2 ;;
  esac
  if [[ "${SKIEW_EMBED_PROVIDER:-$embed_default}" == "openai" ]]; then
    : "${OPENAI_API_KEY:?Set OPENAI_API_KEY or use another embedding provider}"
  fi
}

case "$MODE" in
  test)
    run_tests
    ;;
  smoke)
    run_tests
    run_local_demo
    ;;
  full)
    run_tests
    check_credentials
    for dataset in ${DATASETS:-spider bird}; do
      run_dataset "$dataset"
    done
    ;;
  *)
    echo "Unknown MODE=$MODE (expected test, smoke, or full)" >&2
    exit 2
    ;;
esac
