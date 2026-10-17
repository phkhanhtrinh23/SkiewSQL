from skiewsql import paths


def test_result_artifacts_have_classified_directories():
    assert paths.sqlite_run_dir("spider") == paths.RESULTS_ROOT / "runs/sqlite/spider"
    assert paths.sqlite_run_dir("bird_minidev") == paths.RESULTS_ROOT / "runs/sqlite/bird"
    assert paths.sqlite_run_dir("sqlflow_spider") == paths.RESULTS_ROOT / "runs/sqlite/sqlflow_spider"
    assert paths.benchmark_run_dir("beaver") == paths.RESULTS_ROOT / "runs/beaver"
    assert paths.benchmark_run_dir("bigquery") == paths.RESULTS_ROOT / "runs/bigquery"
    assert paths.SEED_REGISTRIES_DIR == paths.RESULTS_ROOT / "registries/seed"
    assert paths.GROWN_REGISTRIES_DIR == paths.RESULTS_ROOT / "registries/grown"
    assert paths.TABLE_CATALOGS_DIR == paths.RESULTS_ROOT / "catalogs/tables"
