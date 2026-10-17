"""Canonical locations for generated experiment artifacts. Keep path policy here so individual runners cannot gradually repopulate ``results_real`` with unclassified files.  Callers may still expose explicit CLI overrides for external disks."""
from __future__ import annotations

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
RESULTS_ROOT = PACKAGE_DIR / "results_real"

RUNS_ROOT = RESULTS_ROOT / "runs"
SQLITE_RUNS_ROOT = RUNS_ROOT / "sqlite"
BEAVER_RUNS_DIR = RUNS_ROOT / "beaver"
BIGQUERY_RUNS_DIR = RUNS_ROOT / "bigquery"
SNOWFLAKE_RUNS_DIR = RUNS_ROOT / "snowflake"
LIVESQL_RUNS_DIR = RUNS_ROOT / "livesql"
SCIENCE_RUNS_DIR = RUNS_ROOT / "science"

REGISTRIES_ROOT = RESULTS_ROOT / "registries"
SEED_REGISTRIES_DIR = REGISTRIES_ROOT / "seed"
GROWN_REGISTRIES_DIR = REGISTRIES_ROOT / "grown"

TABLE_CATALOGS_DIR = RESULTS_ROOT / "catalogs" / "tables"
ARCHITECTURE_BENCHMARK_DIR = RESULTS_ROOT / "benchmarks" / "architecture"


def sqlite_run_dir(dataset: str) -> Path:
    """Return the output directory for a SQLite-family benchmark dataset."""
    name = str(dataset).strip().lower()
    if name.startswith("sqlflow_"):
        name = "sqlflow_spider"
    elif name.startswith("bird"):
        name = "bird"
    elif name.startswith("spider_"):
        name = "spider"
    return SQLITE_RUNS_ROOT / name


def benchmark_run_dir(benchmark: str) -> Path:
    """Return the run directory used by cross-method baseline adapters."""
    name = str(benchmark).strip().lower()
    mapping = {
        "beaver": BEAVER_RUNS_DIR,
        "bigquery": BIGQUERY_RUNS_DIR,
        "livesql": LIVESQL_RUNS_DIR,
        "spider2lite": sqlite_run_dir("spider2lite"),
    }
    if name not in mapping:
        raise ValueError(f"unknown benchmark artifact directory: {benchmark}")
    return mapping[name]


def ensure_dir(path: Path | str) -> str:
    """Create an artifact directory and return it as a string for os.path callers."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)
