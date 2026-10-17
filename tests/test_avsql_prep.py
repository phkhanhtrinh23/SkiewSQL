"""AV-SQL §4.1 preprocessing port (skiewsql/avsql_prep.py)."""
import sqlite3

from skiewsql import avsql_prep, datasets, realrun, valuelink


def _db():
    con = sqlite3.connect(":memory:")
    years = ", ".join(f"year_{y} REAL" for y in range(2004, 2016))      # 12 same-typed columns
    con.executescript(f"""
        CREATE TABLE ga_sessions_20170201 (visit_id INTEGER PRIMARY KEY, country TEXT, device TEXT);
        CREATE TABLE ga_sessions_20170202 (visit_id INTEGER PRIMARY KEY, country TEXT, device TEXT);
        CREATE TABLE ga_sessions_20170203 (visit_id INTEGER PRIMARY KEY, country TEXT, browser TEXT);
        CREATE TABLE population (country TEXT, {years});
        CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_name TEXT, status TEXT,
                             order_date TEXT, zip_code TEXT,
                             visit_id INTEGER REFERENCES ga_sessions_20170201(visit_id));
        INSERT INTO ga_sessions_20170201 VALUES (1, 'United States', 'mobile');
        INSERT INTO orders VALUES (1, 'Alice', 'Shipped', '2020-01-01', '94110', 1),
                                  (2, 'Bob', 'Pending', '2020-01-02', '10001', 1);
    """)
    return con


def test_table_pattern_matches_av_sql_examples():
    assert avsql_prep.detect_table_pattern("ga_sessions_20170303") == "ga_sessions_{NUM}"
    assert avsql_prep.detect_table_pattern("census_tracts_california") == "census_tracts_{VAR}"
    assert avsql_prep.detect_table_pattern("user_activity_2024_jan") == "user_activity_{NUM}_{VAR}"


def test_tables_merge_only_with_identical_columns():
    sd = avsql_prep.sqlite_schema_dict(_db(), "db")
    groups = avsql_prep.group_tables(sd)
    merged = [m for m in groups.values() if len(m) > 1]
    assert merged == [["ga_sessions_20170201", "ga_sessions_20170202"]]
    assert groups["ga_sessions_20170203"] == ["ga_sessions_20170203"]      # same name pattern, other columns


def test_column_groups_need_ten_same_typed_columns():
    sd = avsql_prep.sqlite_schema_dict(_db(), "db")
    assert avsql_prep.group_columns(sd["population"]) == {
        "year_{NUM}": [f"year_{y}" for y in range(2004, 2016)]}
    nine = {"columns_name": [f"c_{i}" for i in range(9)], "columns_type": ["REAL"] * 9}
    assert avsql_prep.group_columns(nine) == {}
    mixed = {"columns_name": [f"c_{i}" for i in range(10)], "columns_type": ["REAL"] * 9 + ["TEXT"]}
    assert avsql_prep.group_columns(mixed) == {}


def test_chunks_hold_representatives_and_list_siblings():
    prep = avsql_prep.PreparedSchema(avsql_prep.sqlite_schema_dict(_db(), "db"), 10**6, datasets.est_tokens)
    (text, tables), = prep.chunks()
    assert "ga_sessions_20170202" not in tables and "ga_sessions_20170201" in tables
    assert "List of tables have same pattern ga_sessions_{NUM} : ga_sessions_20170201, ga_sessions_20170202" in text
    assert "Columns with pattern 'year_{NUM}': year_2004" in text
    assert text.count("Column: year_") == 0                                # grouped columns are not repeated
    assert "Foreign Key: orders.visit_id -> ga_sessions_20170201.visit_id" in text
    assert "Example Values:[" in text and "Sample rows of this table" in text


def test_split_sorts_by_size_and_respects_the_limit():
    sd = {f"t{i}": {"columns_name": ["c"] * n, "columns_type": ["TEXT"] * n, "columns_description": []}
          for i, n in enumerate([30, 1, 10])}
    parts = avsql_prep.split_by_prompting_size_limit(sd, 60, datasets.est_tokens)
    assert [list(p) for p in parts][0][0] == "t1"                         # smallest table first
    sizes = {t: avsql_prep.estimate_token_count(sd[t], datasets.est_tokens) for t in sd}
    for p in parts:
        assert len(p) == 1 or sum(sizes[t] for t in p) <= 60


def test_filtered_schema_renders_a_sibling_through_its_representative():
    con = _db()
    datasets.prepare_avsql(con, "db", 10**6)
    text = realrun._filtered_schema(con, "", ["ga_sessions_20170202"])
    assert "with representative Table for pattern ga_sessions_{NUM} : ga_sessions_20170201" in text
    assert "Table: orders" not in text


def test_chunk_has_table_reads_the_compact_form():
    from skiewsql import agents
    prep = avsql_prep.PreparedSchema(avsql_prep.sqlite_schema_dict(_db(), "db"), 10**6, datasets.est_tokens)
    (text, _tables), = prep.chunks()
    for t in ("orders", "population", "ga_sessions_20170202", "ga_sessions_20170203"):
        assert agents.chunk_has_table(text, t), t
    assert not agents.chunk_has_table(text, "order")
    assert not agents.chunk_has_table(text, "visit_id")


def test_value_index_follows_av_sql_column_filter():
    con = _db()
    idx = valuelink.get_avsql_index(con, "", "db")
    cols = {(t, c) for _m, t, c, _v in idx.minhashes.values()}
    assert ("orders", "customer_name") in cols and ("orders", "status") in cols
    assert ("orders", "order_date") not in cols and ("orders", "zip_code") not in cols   # name filter
    assert ("orders", "order_id") not in cols                                           # primary key


def test_relevant_values_and_ground():
    idx = avsql_prep.AVSQLValueIndex({"orders": {"status": ["Shipped", "Pending"]},
                                      "visits": {"country": ["United States", "Canada"]}})
    sql = "SELECT * FROM visits WHERE country = 'United Sates' AND 1 = 1"
    texts = idx.relevant_values(sql)
    assert texts == ["Relevant stored values for 'United Sates' in database:\n"
                     "\"United States\" from table 'visits', column 'country'\n"]
    assert idx.ground(sql) == ["literal 'United Sates' is not a DB value. Closest real value is "
                               "'United States' in visits.country — use 'United States'."]
    assert idx.ground("SELECT 1 FROM orders WHERE status = 'Shipped'") == []


def _fake_mysql_run(sql, params=()):
    if "information_schema.COLUMNS" in sql:
        return [("customers", "customer_id", "int(11)", "PRI"), ("customers", "country", "varchar(64)", ""),
                ("orders", "order_id", "int(11)", "PRI"), ("orders", "customer_id", "int(11)", "MUL")]
    if "KEY_COLUMN_USAGE" in sql:
        return [("orders", "customer_id", "customers", "customer_id")]
    if "DISTINCT `country`" in sql:
        return [("United States",), ("Canada",)]
    if sql.startswith("SELECT DISTINCT"):
        return [(1,), (2,)]
    if "FROM `customers` LIMIT" in sql:
        return [(1, "United States")]
    return []


def test_mysql_schema_dict_and_repair_loop(monkeypatch):
    from skiewsql import beaver_method as bm
    from skiewsql.core import SkillRegistry
    sd = avsql_prep.mysql_schema_dict(_fake_mysql_run, "dw")
    assert sd["orders"]["foreign_keys"] == [[["orders", "customer_id"], ["customers", "customer_id"]]]
    assert sd["customers"]["foreign_keys"] == sd["orders"]["foreign_keys"]
    assert sd["customers"]["primary_key"] == ["customer_id"]
    monkeypatch.setitem(bm._AV_PREP, "dw", avsql_prep.PreparedSchema(sd, 10**6, datasets.est_tokens))
    vindex = avsql_prep.AVSQLValueIndex(avsql_prep.unique_values(
        sd, lambda t, c: [r[0] for r in _fake_mysql_run(f"SELECT DISTINCT `{c}` FROM `{t}`")]))

    class Client:
        def validate(self, sql, db):
            return True, "ok", ["customer_id", "country"]

    prompts = []

    class LLM:
        def ask(self, _sys, user, tag="", **_kw):
            prompts.append(user)
            first = len(prompts) == 1
            lit = "United Sates" if first else "United States"
            cols = '["customer_id"]' if first else '["customer_id", "country"]'
            return (f"```sql\nSELECT customer_id, country FROM customers WHERE country = '{lit}'\n```\n"
                    f'```json\n{{"think": "x", "customers": {cols}}}\n```')

    g = SkillRegistry(db_id="dw")
    v = bm.gen_av_view(LLM(), Client(), g, "dw", "schema", "q", "chunk_view_0", "", vindex)
    assert v is not None and g.has("chunk_view_0") and len(prompts) == 2
    # attempt 1 is inconsistent (country not selected) -> its feedback carries the retrieved value
    assert "Relevant stored values for 'United Sates'" in prompts[1]
    assert "columns used in the CTE but not selected" in prompts[1]
