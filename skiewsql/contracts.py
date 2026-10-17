"""contracts.py — complete, validated skill contracts (contract v3) for the skill registry.

A stored view is only safe to reuse when its contract says what it really is. This module derives that contract from the SQL and the live database instead of trusting the generator's self-report:

  * identity      : `sql_hash` / `skill_id` from dialect + normalized SQL + dependency hashes (stable across renames).
  * schema version: per-table fingerprints (column names + types), so a skill goes stale only when a table it reads changes.
  * outputs       : the columns the view actually returns when executed.
  * grain         : `grain_kind` = scalar | keyed | unknown. GROUP BY is authoritative. Otherwise a key is accepted only when it is structural (a projected primary key) or verified unique on the data. An empty grain never silently means "scalar".
  * semantics     : intrinsic filters (equality, numeric and date ranges, BETWEEN), per-output aggregation kind, join keys, lineage.
  * validation    : execution, declared outputs, grain uniqueness, scalar row count, filter assertions, join cardinality, row count, and optional LLM-generated test queries.

Execution alone only proves a view runs. These assertions check the claims retrieval relies on (grain, filters, fan-out)."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import sqlglot
from sqlglot import expressions as exp

from skiewsql import datasets
from skiewsql.core import SkillRegistry, ViewSpec, norm_key

CONTRACT_VERSION = 3
GRAIN_SCALAR, GRAIN_KEYED, GRAIN_UNKNOWN = "scalar", "keyed", "unknown"
MEASURE_KINDS = {"sum", "count", "count_distinct", "avg", "min", "max", "agg_expr", "agg_other"}
# Re-aggregation that is exact when rolling a finer grain up to a coarser one.
DECOMPOSABLE = {"sum": "SUM", "count": "SUM", "min": "MIN", "max": "MAX"}
ASSERT_TIMEOUT = 10.0
_ISO_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?)?)?$")
_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Scope: what a skill must match to be usable here (database, dialect, table versions)
# --------------------------------------------------------------------------- #
@dataclass
class Scope:
    db_id: str
    dialect: str = "sqlite"
    table_fp: Dict[str, str] = field(default_factory=dict)      # lower(table) -> interface fingerprint
    data_fp: Dict[str, str] = field(default_factory=dict)       # lower(table) -> data stamp (row count, max rowid)
    model: str = ""
    prompt_version: str = ""

    @property
    def tables(self) -> set:
        return set(self.table_fp)


# Grain bases that were only OBSERVED on the data (not guaranteed by the SQL or a key constraint). New rows can break them, so these skills are tied to a data stamp.
DATA_DERIVED_GRAIN = {"verified_unique", "distinct"}


def table_fingerprint(con, table: str) -> str:
    """Fingerprint of one table's interface: name, (column, declared type, not-null, PK position), unique indexes, and foreign keys. Row data is excluded (see `data_fingerprint`)."""
    cols = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    sig = sorted((str(c[1]).lower(), str(c[2] or "").upper(), int(c[3] or 0), int(c[5] or 0)) for c in cols)
    uniq = []
    for idx in con.execute(f'PRAGMA index_list("{table}")').fetchall():
        if idx[2]:                                            # unique index / UNIQUE / PRIMARY KEY constraint
            cols_i = [str(r[2]).lower() for r in con.execute(f'PRAGMA index_info("{idx[1]}")').fetchall()]
            uniq.append(sorted(cols_i))
    fks = sorted((str(f[2]).lower(), str(f[3]).lower(), str(f[4]).lower())
                 for f in con.execute(f'PRAGMA foreign_key_list("{table}")').fetchall())
    return hashlib.sha1(json.dumps([table.lower(), sig, sorted(uniq), fks]).encode()).hexdigest()[:16]


def data_fingerprint(con, table: str) -> str:
    """Cheap data stamp: row count and max rowid. It changes when rows are added or deleted."""
    try:
        row = con.execute(f'SELECT COUNT(*), MAX(rowid) FROM "{table}"').fetchone()
    except Exception:  # noqa: BLE001 — WITHOUT ROWID tables
        row = con.execute(f'SELECT COUNT(*), NULL FROM "{table}"').fetchone()
    return f"{row[0]}:{row[1]}"


def make_scope(con, db_id: str, dialect: str = "sqlite", model: str = "",
               prompt_version: str = "") -> Scope:
    tables = datasets.list_tables(con)
    fps = {t.lower(): table_fingerprint(con, t) for t in tables}
    dfps = {t.lower(): data_fingerprint(con, t) for t in tables}
    return Scope(db_id=db_id, dialect=dialect, table_fp=fps, data_fp=dfps, model=model,
                 prompt_version=prompt_version)


def schema_fingerprint(scope: Scope) -> str:
    return hashlib.sha1(json.dumps(sorted(scope.table_fp.items())).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Parsing helpers (sqlglot 18.x uses args "with"/"from", 30.x uses "with_"/"from_")
# --------------------------------------------------------------------------- #
def parse(sql: str, dialect: str = "sqlite"):
    try:
        return sqlglot.parse_one(sql, read=dialect)
    except Exception:  # noqa: BLE001
        return None


def with_of(tree):
    if tree is None:
        return None
    return tree.args.get("with_") or tree.args.get("with")


def set_with(tree, value):
    key = "with_" if "with_" in tree.arg_types else "with"
    tree.set(key, value)


def outer_select(tree):
    """The top-level SELECT whose projection defines the relation (None for set operations)."""
    if isinstance(tree, exp.Select):
        return tree
    if isinstance(tree, exp.Subquery):
        return outer_select(tree.this)
    return None


def normalize_sql(sql: str, dialect: str = "sqlite") -> str:
    """Canonical text used for hashing: parsed, identifiers normalized, comments dropped. Falls back to lowercase collapsed whitespace when parsing fails."""
    tree = parse(sql or "", dialect)
    if tree is not None:
        try:
            from sqlglot.optimizer.normalize_identifiers import normalize_identifiers
            return normalize_identifiers(tree, dialect=dialect).sql(dialect=dialect, comments=False)
        except Exception:  # noqa: BLE001
            try:
                return tree.sql(dialect=dialect, comments=False)
            except Exception:  # noqa: BLE001
                pass
    return re.sub(r"\s+", " ", (sql or "").strip().lower())


def sql_hash(spec: ViewSpec, graph: Optional[SkillRegistry] = None, _seen=None) -> str:
    """Content hash of a view: dialect, normalized body, and the hashes of its dependencies (so two views with the same text over different dependency definitions differ)."""
    _seen = _seen or set()
    deps = []
    for d in sorted(spec.depends_on or []):
        dep = graph.views.get(d) if graph is not None else None
        if dep is None or d in _seen:
            deps.append(f"name:{d.lower()}")
        else:
            deps.append(dep.sql_hash or sql_hash(dep, graph, _seen | {spec.name}))
    raw = "\n".join([spec.dialect or "sqlite", normalize_sql(spec.body_sql, spec.dialect or "sqlite"), *deps])
    return hashlib.sha256(raw.encode()).hexdigest()


def skill_id_for(h: str) -> str:
    return "sk_" + h[:16]


def rename_table_refs(sql: str, old: str, new: str, dialect: str = "sqlite") -> str:
    """Rewrite references to table/CTE `old` as `new` (used when a promoted view's dependency is merged into an existing skill)."""
    tree = parse(sql, dialect)
    if tree is None:
        return re.sub(rf"\b{re.escape(old)}\b", new, sql)
    for t in tree.find_all(exp.Table):
        if t.name.lower() == old.lower():
            t.set("this", exp.to_identifier(new))
    return tree.sql(dialect=dialect)


# --------------------------------------------------------------------------- #
# Static analysis of a view body
# --------------------------------------------------------------------------- #
def _col_key(e) -> str:
    return e.name if isinstance(e, exp.Column) else e.sql()


def _split_and(cond):
    if isinstance(cond, exp.And):
        return _split_and(cond.left) + _split_and(cond.right)
    if isinstance(cond, exp.Paren):
        return _split_and(cond.this)
    return [cond]


def _literal(e) -> Optional[Tuple[str, bool]]:
    """(text, is_string) for a literal, or None."""
    if isinstance(e, exp.Literal):
        return e.name, bool(e.is_string)
    if isinstance(e, exp.Boolean):
        return str(e.this).lower(), False
    if isinstance(e, exp.Neg) and isinstance(e.this, exp.Literal) and not e.this.is_string:
        return "-" + e.this.name, False
    return None


def _bound(op: str, lit: Tuple[str, bool]) -> Optional[str]:
    text, is_str = lit
    if not is_str and _NUM.match(text):
        return f"{op}{text}"
    if is_str and _ISO_DATE.match(text):              # time window: ISO dates order lexicographically
        return f"{op}{text}"
    return None


_FLIP = {">": "<", "<": ">", ">=": "<=", "<=": ">="}


def extract_filters(sel) -> Dict[str, str]:
    """Intrinsic filters from the outermost WHERE. Equality to a literal keeps the bare value. Numeric or ISO-date inequalities and BETWEEN become ';'-joined bounds (e.g. '>=2020-01-01;<2021-01-01'), which `interval_contains` compares. OR branches, IS NULL and non-orderable ranges are skipped (a safe miss)."""
    out: Dict[str, List[str]] = {}
    where = sel.args.get("where") if sel is not None else None
    if where is None:
        return {}
    for cond in _split_and(where.this):
        if isinstance(cond, exp.EQ):
            col, lit = (cond.left, _literal(cond.right)) if isinstance(cond.left, exp.Column) else \
                       (cond.right, _literal(cond.left))
            if isinstance(col, exp.Column) and lit is not None:
                out.setdefault(_col_key(col), []).append(lit[0])
            continue
        if isinstance(cond, exp.Between) and isinstance(cond.this, exp.Column):
            lo, hi = _literal(cond.args.get("low")), _literal(cond.args.get("high"))
            if lo and hi:
                a, b = _bound(">=", lo), _bound("<=", hi)
                if a and b:
                    out.setdefault(_col_key(cond.this), []).extend([a, b])
            continue
        for cls, op in ((exp.GTE, ">="), (exp.LTE, "<="), (exp.GT, ">"), (exp.LT, "<")):
            if isinstance(cond, cls):
                if isinstance(cond.left, exp.Column) and _literal(cond.right):
                    b = _bound(op, _literal(cond.right))
                    col = cond.left
                elif isinstance(cond.right, exp.Column) and _literal(cond.left):
                    b = _bound(_FLIP[op], _literal(cond.left))
                    col = cond.right
                else:
                    b = None
                if b:
                    out.setdefault(_col_key(col), []).append(b)
                break
    res = {}
    for col, vals in out.items():
        eq = [v for v in vals if not is_range(v)]
        rg = [v for v in vals if is_range(v)]
        if eq:
            res[col] = eq[0]                              # contradictory equalities are the SQL's problem
        elif rg:
            res[col] = ";".join(rg)
    return res


def _plain_aggs(node, sel):
    """Aggregate calls in `node` that belong to `sel` itself (not a window, not a nested subquery)."""
    for agg in node.find_all(exp.AggFunc):
        if agg.find_ancestor(exp.Window) is not None:
            continue
        if agg.find_ancestor(exp.Select) is not sel:
            continue
        yield agg


def _agg_kind(proj, sel, group_keys_norm) -> str:
    inner = proj.unalias() if isinstance(proj, exp.Alias) else proj
    if isinstance(inner, exp.Window):
        return "window"
    if isinstance(inner, exp.AggFunc) and inner.find_ancestor(exp.Window) is None:
        if isinstance(inner, exp.Count):
            return "count_distinct" if isinstance(inner.this, exp.Distinct) else "count"
        for cls, kind in ((exp.Sum, "sum"), (exp.Avg, "avg"), (exp.Min, "min"), (exp.Max, "max")):
            if isinstance(inner, cls):
                return kind
        return "agg_other"
    if any(True for _ in _plain_aggs(inner, sel)):
        return "agg_expr"                                 # e.g. SUM(a)/COUNT(b): not re-aggregable
    if inner.find(exp.Window) is not None:
        return "window"
    name = proj.alias_or_name
    if norm_key(name) in group_keys_norm or norm_key(inner.sql()) in group_keys_norm:
        return "key"
    return "none"


@dataclass
class SqlFacts:
    parsed: bool = False
    base_tables: List[str] = field(default_factory=list)
    view_refs: List[str] = field(default_factory=list)
    group_keys: List[str] = field(default_factory=list)
    has_group: bool = False
    has_agg: bool = False
    has_window: bool = False
    rank_window: bool = False
    distinct: bool = False
    set_op: str = ""                                      # union | union_all | intersect | except | ""
    filters: Dict[str, str] = field(default_factory=dict)
    aggregation: Dict[str, str] = field(default_factory=dict)
    joins: List[Dict[str, str]] = field(default_factory=list)
    projected: Dict[str, str] = field(default_factory=dict)   # output name -> "table.column" when a plain column


_OPERATOR_ORDER = ("filter", "join", "project", "distinct", "aggregate", "window", "set", "sort", "limit", "recursive")


def _operator_profile(tree, facts: SqlFacts) -> List[str]:
    """Compact relational operator vocabulary used for retrieval and structural deduplication."""
    present = {"project"}
    if tree.find(exp.Where) is not None:
        present.add("filter")
    if tree.find(exp.Join) is not None:
        present.add("join")
    if facts.distinct:
        present.add("distinct")
    if facts.has_group or facts.has_agg:
        present.add("aggregate")
    if facts.has_window:
        present.add("window")
    if facts.set_op:
        present.add("set")
    if tree.find(exp.Order) is not None:
        present.add("sort")
    if tree.find(exp.Limit) is not None:
        present.add("limit")
    w = with_of(tree)
    if w is not None and bool(w.args.get("recursive")):
        present.add("recursive")
    return [op for op in _OPERATOR_ORDER if op in present]


def _parameter_name(node) -> str:
    if isinstance(node, exp.Placeholder):
        return str(node.name or "").lstrip(":@$?")
    if isinstance(node, exp.Parameter):
        return str(node.name or node.this or "").lstrip(":@$?")
    if isinstance(node, exp.Column) and node.name.startswith("$"):
        return node.name[1:]
    return ""


def relational_provenance(con, graph: SkillRegistry, spec: ViewSpec, facts: SqlFacts,
                          outputs: List[str]) -> Dict:
    """Derive compact relation, column, operator and parameter provenance from SQL.

    This is definition-level provenance. It deliberately does not store per-row provenance in the
    registry. Column lineage is expanded through dependency skills when their metadata permits it.
    """
    tree = parse(spec.body_sql or "", spec.dialect or "sqlite")
    if tree is None:
        return {"source_columns": [], "output_lineage": {}, "operators": [],
                "upstream_skills": list(spec.depends_on or []), "parameter_bindings": {}}

    def direct_sources(sel):
        tables = []
        for t in sel.find_all(exp.Table):
            if t.find_ancestor(exp.Select) is sel:
                tables.append(t)
        return tables

    def resolve(col) -> str:
        sel = col.find_ancestor(exp.Select)
        tables = direct_sources(sel) if sel is not None else []
        aliases = {}
        for t in tables:
            aliases[(t.alias_or_name or t.name).lower()] = t.name
            aliases[t.name.lower()] = t.name
        table = aliases.get((col.table or "").lower(), col.table) if col.table else ""
        if not table and len(tables) == 1:
            table = tables[0].name
        if not table and tables:
            owners = []
            for t in tables:
                if t.name in graph.views:
                    cols = graph.views[t.name].output_columns
                else:
                    try:
                        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t.name}")').fetchall()]
                    except Exception:  # noqa: BLE001
                        cols = []
                if norm_key(col.name) in {norm_key(c) for c in cols}:
                    owners.append(t.name)
            if len(owners) == 1:
                table = owners[0]
        return f"{table}.{col.name}" if table else col.name

    def expand(ref: str) -> List[str]:
        if "." not in ref:
            return [ref]
        table, column = ref.rsplit(".", 1)
        dep = graph.views.get(table)
        if dep is None:
            return [ref]
        lineage_map = (dep.provenance or {}).get("output_lineage") or {}
        by = {norm_key(k): v for k, v in lineage_map.items()}
        return list(by.get(norm_key(column)) or [ref])

    source_columns = []
    for col in tree.find_all(exp.Column):
        if not col.name or col.name.startswith("$") or isinstance(col.this, exp.Star):
            continue
        for ref in expand(resolve(col)):
            if ref not in source_columns:
                source_columns.append(ref)

    output_lineage: Dict[str, List[str]] = {}
    sel = outer_select(tree)
    if sel is not None:
        projections = {norm_key(p.alias_or_name): p for p in sel.expressions
                       if p.alias_or_name and not isinstance(p, exp.Star)}
        for output in outputs:
            proj = projections.get(norm_key(output))
            refs = []
            if proj is not None:
                for col in proj.find_all(exp.Column):
                    if col.find_ancestor(exp.Select) is sel and not isinstance(col.this, exp.Star):
                        refs.extend(expand(resolve(col)))
            if not refs:
                matches = [r for r in source_columns if norm_key(r.rsplit(".", 1)[-1]) == norm_key(output)]
                if len(matches) == 1:
                    refs = matches
            output_lineage[output] = list(dict.fromkeys(refs))

    parameter_bindings = {}
    for pred in tree.find_all(exp.EQ):
        pairs = ((pred.left, pred.right), (pred.right, pred.left))
        for col, parameter in pairs:
            name = _parameter_name(parameter)
            if isinstance(col, exp.Column) and name:
                parameter_bindings[name] = resolve(col)
                break

    dep_columns = []
    dep_operators = []
    for dep_name in spec.depends_on or []:
        dep = graph.views.get(dep_name)
        if dep is None:
            continue
        dep_columns.extend((dep.provenance or {}).get("source_columns") or [])
        dep_operators.extend((dep.provenance or {}).get("operators") or [])
    return {
        "source_columns": list(dict.fromkeys(source_columns + dep_columns)),
        "output_lineage": output_lineage,
        "operators": [op for op in _OPERATOR_ORDER
                      if op in set(_operator_profile(tree, facts) + dep_operators)],
        "upstream_skills": list(spec.depends_on or []),
        "parameter_bindings": parameter_bindings,
    }


def analyze_sql(body: str, view_names=(), dialect: str = "sqlite") -> SqlFacts:
    """Best-effort static facts about a view body. Never raises."""
    f = SqlFacts()
    tree = parse(body or "", dialect)
    if tree is None:
        return f
    f.parsed = True
    views_l = {v.lower() for v in view_names}
    inner_ctes = set()
    w = with_of(tree)
    if w is not None:
        inner_ctes = {c.alias.lower() for c in w.expressions}
    seen = set()
    for t in tree.find_all(exp.Table):
        n = t.name
        if not n or n.lower() in seen:
            continue
        seen.add(n.lower())
        if n.lower() in views_l:
            f.view_refs.append(n)
        elif n.lower() not in inner_ctes:
            f.base_tables.append(n)
    if isinstance(tree, exp.Union):
        f.set_op = "union" if tree.args.get("distinct") else "union_all"
    elif isinstance(tree, exp.Intersect):
        f.set_op = "intersect"
    elif isinstance(tree, exp.Except):
        f.set_op = "except"
    sel = outer_select(tree)
    if sel is None:
        return f
    f.distinct = bool(sel.args.get("distinct"))
    proj = {}
    for e in sel.expressions:
        if isinstance(e, exp.Alias):
            proj[e.this.sql()] = e.alias
        elif isinstance(e, exp.Column):
            proj[e.sql()] = e.name
    grp = sel.args.get("group")
    if grp is not None and grp.expressions:
        f.has_group = True
        for e in grp.expressions:
            if isinstance(e, exp.Column):
                f.group_keys.append(proj.get(e.sql(), e.name))
            elif isinstance(e, exp.Literal) and not e.is_string and e.name.isdigit():
                i = int(e.name) - 1                        # GROUP BY 1
                if 0 <= i < len(sel.expressions):
                    f.group_keys.append(sel.expressions[i].alias_or_name)
            else:
                f.group_keys.append(proj.get(e.sql(), e.sql()))
    gk = {norm_key(g) for g in f.group_keys}
    for e in sel.expressions:
        if isinstance(e, exp.Star) or (isinstance(e, exp.Column) and isinstance(e.this, exp.Star)):
            continue
        kind = _agg_kind(e, sel, gk)
        f.aggregation[e.alias_or_name] = kind
        if kind == "window":
            f.has_window = True
        inner = e.unalias() if isinstance(e, exp.Alias) else e
        if isinstance(inner, exp.Column):
            f.projected[e.alias_or_name] = f"{inner.table}.{inner.name}" if inner.table else inner.name
    f.has_agg = any(True for e in sel.expressions for _ in _plain_aggs(e, sel)) or \
        sel.args.get("having") is not None and not f.has_group
    f.rank_window = any(isinstance(w.this, (exp.RowNumber, exp.Rank, exp.DenseRank))
                        for w in sel.find_all(exp.Window))
    f.filters = extract_filters(sel)
    alias_to_table = {}
    for t in sel.find_all(exp.Table):
        alias_to_table[(t.alias_or_name or t.name).lower()] = t.name
    for j in sel.args.get("joins") or []:
        on = j.args.get("on")
        if on is None:
            continue
        for cond in _split_and(on):
            if isinstance(cond, exp.EQ) and isinstance(cond.left, exp.Column) and isinstance(cond.right, exp.Column):
                lt = alias_to_table.get((cond.left.table or "").lower(), cond.left.table)
                rt = alias_to_table.get((cond.right.table or "").lower(), cond.right.table)
                f.joins.append({"left_table": lt, "left_col": cond.left.name,
                                "right_table": rt, "right_col": cond.right.name})
    return f


def selection_consistency(body: Optional[str], selection: Optional[Dict[str, List[str]]], con,
                          dialect: str = "sqlite") -> List[str]:
    """AV-SQL rule-based consistency between a CTE and its JSON schema selection J = {table: [columns]} (dropped tables already removed). Returns problem messages (empty = consistent):
      1. an empty selection must mean no CTE;
      2. a CTE must come with at least one selected table or column;
      3. every table and column the CTE uses must appear in the selection."""
    sel = {str(t).lower(): {str(c).split(".")[-1].strip('`"').lower() for c in cols}
           for t, cols in (selection or {}).items()}
    has_cte = bool((body or "").strip())
    if not has_cte:
        return []
    if not sel:                                           # rules 1 + 2
        return ["the JSON selects no table or column but a CTE was written: select the tables/columns the "
                "CTE uses, or mark every table \"drop_all\" and write no CTE"]
    tree = parse(body, dialect)
    if tree is None:
        return []                                         # unparseable: execution feedback covers it
    inner = {c.alias.lower() for c in (with_of(tree).expressions if with_of(tree) is not None else [])}
    alias = {}
    tables = []
    for t in tree.find_all(exp.Table):
        if not t.name or t.name.lower() in inner:
            continue
        alias[(t.alias_or_name or t.name).lower()] = t.name
        alias[t.name.lower()] = t.name
        if t.name not in tables:
            tables.append(t.name)
    problems = []
    missing_tables = [t for t in tables if t.lower() not in sel]
    if missing_tables:
        problems.append(f"tables used in the CTE but not selected in the JSON: {missing_tables}")
    cols_of = {}
    for t in tables:
        try:
            cols_of[t] = {str(c[1]).lower() for c in con.execute(f'PRAGMA table_info("{t}")').fetchall()}
        except Exception:  # noqa: BLE001
            cols_of[t] = set()
    lacking = []
    for col in tree.find_all(exp.Column):
        if isinstance(col.this, exp.Star) or not col.name:
            continue
        name = col.name.lower()
        if col.table:
            t = alias.get(col.table.lower())
            if t is None:                                 # qualified by an inner CTE / subquery alias
                continue
            owners = [t]
        else:
            owners = [t for t in tables if name in cols_of.get(t, set())]
            if not owners:                                # an output alias (ORDER BY total) or unknown
                continue
        if not any(name in sel.get(t.lower(), set()) for t in owners):
            key = f"{owners[0]}.{col.name}"
            if key not in lacking:
                lacking.append(key)
    if lacking:
        problems.append("columns used in the CTE but not selected in the JSON: " + ", ".join(lacking[:20]))
    return problems


def infer_category(facts: SqlFacts, default: str = "SEL") -> str:
    """Category implied by the SQL shape (used for promoted AV-SQL chunk views, which are generated without one)."""
    if not facts.parsed:
        return default
    if facts.set_op:
        return "SET"
    if facts.has_group or facts.has_agg:
        return "AGG"
    if facts.rank_window:
        return "RANK"
    if facts.has_window:
        return "WIN"
    if facts.joins or len(facts.base_tables) + len(facts.view_refs) > 1:
        return "JOIN"
    return default


def question_constants(body: str, question: str, dialect: str = "sqlite", extra_texts=()) -> List[str]:
    """Literals in `body` that also appear in the question (or `extra_texts`, e.g. its evidence), matched case-insensitively on word boundaries. Conservative on purpose: casing cannot tell an intrinsic concept value ('completed') from a question constant ('france'), so any literal the question mentions blocks promotion. A promoted relation must not keep them."""
    tree = parse(body or "", dialect)
    if tree is None:
        return []
    qtext = " ".join([question or "", *[str(t) for t in extra_texts if t]]).lower()
    found = []
    for lit in tree.find_all(exp.Literal):
        v = lit.name
        if not v or v in ("0", "1"):
            continue
        if re.search(rf"(?<![\w.]){re.escape(v.lower())}(?![\w])", qtext):
            found.append(v)
    return found


# --------------------------------------------------------------------------- #
# Range / time-window containment
# --------------------------------------------------------------------------- #
_ORD_OPS = ("<=", ">=", "<", ">")


def is_range(v) -> bool:
    return isinstance(v, str) and v.strip().startswith(_ORD_OPS)


def _bound_val(text: str):
    text = text.strip().strip("'\"")
    if _NUM.match(text):
        return float(text)
    if _ISO_DATE.match(text):
        return text
    return None


def parse_interval(v: str):
    """'>=a;<b' -> (lo, lo_incl, hi, hi_incl). None when a bound is not orderable."""
    lo, lo_incl, hi, hi_incl = None, True, None, True
    for part in str(v).split(";"):
        part = part.strip()
        for op in ("<=", ">=", "<", ">"):
            if part.startswith(op):
                val = _bound_val(part[len(op):])
                if val is None:
                    return None
                if op in (">", ">="):
                    if lo is None or _gt(val, lo):
                        lo, lo_incl = val, op == ">="
                else:
                    if hi is None or _gt(hi, val):
                        hi, hi_incl = val, op == "<="
                break
        else:
            return None
    return lo, lo_incl, hi, hi_incl


def _gt(a, b) -> bool:
    if type(a) is not type(b):
        raise TypeError("mixed bound types")
    return a > b


def interval_contains(view_v: str, req_v: str) -> bool:
    """True iff the view's interval contains the request's (the view keeps every row the request needs, and the tighter bound can be applied downstream)."""
    pv, pq = parse_interval(view_v), parse_interval(req_v)
    if pv is None or pq is None:
        return False
    vlo, vlo_i, vhi, vhi_i = pv
    qlo, qlo_i, qhi, qhi_i = pq
    try:
        if vlo is not None:
            if qlo is None or _gt(vlo, qlo) or (vlo == qlo and not vlo_i and qlo_i):
                return False
        if vhi is not None:
            if qhi is None or _gt(qhi, vhi) or (vhi == qhi and not vhi_i and qhi_i):
                return False
    except TypeError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Executing a view with its dependency closure
# --------------------------------------------------------------------------- #
def _order(specs: List[ViewSpec]) -> List[ViewSpec]:
    by = {s.name: s for s in specs}
    ordered, visiting, done = [], set(), set()

    def visit(name):
        if name in done:
            return
        if name in visiting:
            raise ValueError(f"cyclic ViewSpec dependency at {name}")
        visiting.add(name)
        for dependency in by[name].depends_on:
            if dependency in by:
                visit(dependency)
        visiting.remove(name)
        done.add(name)
        ordered.append(by[name])

    for name in by:
        visit(name)
    return ordered


def closure_sql(graph: SkillRegistry, spec: ViewSpec, select: str) -> str:
    """`WITH <closure of spec> <select>`. `select` refers to the view by its name."""
    deps = graph.topo_closure(spec.depends_on) if spec.depends_on else []
    chosen = {s.name: s for s in deps}
    chosen[spec.name] = spec
    ordered = _order(list(chosen.values()))
    prefix = "WITH RECURSIVE" if any(s.category == "REC" for s in ordered) else "WITH"
    return f"{prefix} " + ",\n".join(s.cte_clause() for s in ordered) + "\n" + select


def q(ident: str) -> str:
    return '"' + str(ident).replace('"', '""') + '"'


def output_columns(con, graph: SkillRegistry, spec: ViewSpec) -> List[str]:
    """Column names the view actually returns (LIMIT 0: prepared, no rows scanned). Raises on a bad view."""
    cur = con.execute(closure_sql(graph, spec, f"SELECT * FROM {spec.name} LIMIT 0"))
    return [d[0] for d in cur.description]


def _scalar(con, sql: str, timeout: float):
    rows = datasets.run_sql(con, sql, timeout)
    return rows[0][0] if rows and rows[0] else None


def literal_sql(value: str, numeric: bool) -> str:
    v = str(value).strip()
    if numeric and _NUM.match(v):
        return v
    return "'" + v.strip("'\"").replace("'", "''") + "'"


def norm_value(v) -> str:
    """Filter value as compared across contracts: no surrounding quotes, no leading '=', lowercase."""
    s = str(v).strip()
    if s.startswith("=") and not s.startswith("=="):
        s = s[1:].strip()
    return s.strip("'\"").strip().lower()


def filter_sql(col: str, value: str, prefix: str = "") -> Optional[str]:
    """Predicate that is TRUE for rows satisfying the filter `col` op value (value format as in semantic_filters)."""
    c = prefix + q(col)
    if is_range(value):
        parts = []
        for part in str(value).split(";"):
            part = part.strip()
            for op in ("<=", ">=", "<", ">"):
                if part.startswith(op):
                    val = part[len(op):].strip()
                    parts.append(f"{c} {op} {literal_sql(val, bool(_NUM.match(val.strip(chr(39) + chr(34)))))}")
                    break
        return " AND ".join(parts) if parts else None
    v = str(value).strip()
    if v.startswith("=") and not v.startswith("=="):
        v = v[1:].strip()
    v = v.strip("'\"")
    if v.lower() in ("true", "false"):                    # SQLite stores booleans as 1/0
        return f"({c} = {int(v.lower() == 'true')} OR {c} = '{v}')"
    if _NUM.match(v):
        return f"({c} = {v} OR {c} = '{v}')"
    return f"{c} = {literal_sql(v, False)}"


def filter_violation_sql(col: str, value: str) -> Optional[str]:
    """Predicate that is TRUE for a row violating the declared filter `col` op value."""
    p = filter_sql(col, value)
    return f"NOT ({p})" if p else None


# --------------------------------------------------------------------------- #
# Grain derivation
# --------------------------------------------------------------------------- #
def _pk_columns(con, table: str) -> List[str]:
    try:
        cols = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    except Exception:  # noqa: BLE001
        return []
    pk = sorted((c for c in cols if c[5]), key=lambda c: c[5])
    return [c[1] for c in pk]


def _unique_on(con, graph, spec, cols: List[str], timeout: float) -> Optional[bool]:
    if not cols:
        return None
    keys = ", ".join(q(c) for c in cols)
    sql = closure_sql(graph, spec, f"SELECT COUNT(*) FROM (SELECT 1 FROM {spec.name} "
                                    f"GROUP BY {keys} HAVING COUNT(*) > 1)")
    try:
        return int(_scalar(con, sql, timeout) or 0) == 0
    except datasets.ExecError:
        return None


def _match_outputs(names, outputs) -> Optional[List[str]]:
    """Map names onto actual output columns by normalized key. None if any is missing."""
    by = {norm_key(o): o for o in outputs}
    res = []
    for n in names:
        m = by.get(norm_key(n)) or by.get(norm_key(str(n).split(".")[-1]))
        if m is None:
            return None
        res.append(m)
    return res


def derive_grain(con, graph, spec, facts: SqlFacts, outputs: List[str], row_count: Optional[int],
                 timeout: float = ASSERT_TIMEOUT) -> Tuple[str, List[str], str]:
    """(grain_kind, grain, basis). basis records why the grain is trusted: group_by, scalar_aggregate, distinct, primary_key, verified_unique, or unverifiable."""
    if facts.has_group:
        keys = _match_outputs(facts.group_keys, outputs)
        return GRAIN_KEYED, (keys if keys is not None else list(facts.group_keys)), "group_by"
    if facts.has_agg and not facts.has_window and not facts.set_op:
        return GRAIN_SCALAR, [], "scalar_aggregate"
    if (facts.distinct or facts.set_op == "union") and outputs:
        ok = _unique_on(con, graph, spec, outputs, timeout)
        return (GRAIN_KEYED, list(outputs), "distinct") if ok is not False else (GRAIN_UNKNOWN, [], "unverifiable")
    # Single base table, no joins, no view dependency, and every PK column projected -> structural key.
    if len(facts.base_tables) == 1 and not facts.joins and not facts.view_refs and not facts.set_op:
        pk = _pk_columns(con, facts.base_tables[0])
        if pk:
            back = {norm_key(v.split(".")[-1]): k for k, v in facts.projected.items()}
            mapped = [back.get(norm_key(c)) for c in pk]
            if all(mapped):
                return GRAIN_KEYED, mapped, "primary_key"
    if not row_count:
        return GRAIN_UNKNOWN, [], "unverifiable"          # an empty view proves no key
    tried = []
    declared = _match_outputs(spec.grain, outputs) if spec.grain else None
    if declared:
        tried.append(declared)
    for t in facts.base_tables:
        pk = _match_outputs(_pk_columns(con, t), outputs)
        if pk and pk not in tried:
            tried.append(pk)
    ids = [o for o in outputs if norm_key(o) == "id" or norm_key(o).endswith("id")]
    for c in ids:
        if [c] not in tried:
            tried.append([c])
    for cand in tried[:6]:
        if _unique_on(con, graph, spec, cand, timeout) is True:
            return GRAIN_KEYED, cand, "verified_unique"
    return GRAIN_UNKNOWN, [], "unverifiable"


# --------------------------------------------------------------------------- #
# Validation (contract assertions)
# --------------------------------------------------------------------------- #
def validate(con, graph: SkillRegistry, spec: ViewSpec, timeout: float = ASSERT_TIMEOUT,
             tests: Optional[List[Dict]] = None) -> Dict:
    """Run the contract assertions for `spec` (already added to `graph` or closure-resolvable). Returns the validation record. Assertions that time out are 'inconclusive', not failures."""
    rec = {"validated_at": now_iso(), "contract_version": CONTRACT_VERSION, "failures": []}
    try:
        datasets.run_sql(con, closure_sql(graph, spec, f"SELECT * FROM {spec.name} LIMIT 5"), timeout)
        cols = output_columns(con, graph, spec)
    except Exception as e:  # noqa: BLE001
        rec.update(executed=False, error=str(e)[:300], passed=False)
        rec["failures"].append(f"execution: {str(e)[:200]}")
        return rec
    rec["executed"], rec["columns"] = True, cols
    missing = [c for c in spec.output_columns if norm_key(c) not in {norm_key(x) for x in cols}]
    if missing:
        rec["failures"].append(f"declared outputs missing: {missing}")
    try:
        rec["row_count"] = int(_scalar(con, closure_sql(graph, spec, f"SELECT COUNT(*) FROM {spec.name}"), timeout) or 0)
    except datasets.ExecError:
        rec["row_count"] = None
    # grain
    if spec.grain_kind == GRAIN_KEYED and spec.grain:
        keys = _match_outputs(spec.grain, cols)
        if keys is None:
            rec["grain_check"] = "fail"
            rec["failures"].append(f"grain keys {spec.grain} are not output columns")
        else:
            uniq = _unique_on(con, graph, spec, keys, timeout)
            rec["grain_check"] = {True: "pass", False: "fail", None: "inconclusive"}[uniq]
            if uniq is False:
                rec["failures"].append(f"duplicate rows per declared grain {keys}: the view is not one row per {keys}")
    elif spec.grain_kind == GRAIN_SCALAR:
        ok = rec.get("row_count") is not None and rec["row_count"] <= 1
        rec["grain_check"] = "pass" if ok else ("inconclusive" if rec.get("row_count") is None else "fail")
        if rec["grain_check"] == "fail":
            rec["failures"].append(f"scalar view returned {rec['row_count']} rows")
    else:
        rec["grain_check"] = "n/a"
    # filters: only checkable when the filter column is exposed
    fchecks = {}
    for col, val in (spec.semantic_filters or {}).items():
        oc = _match_outputs([col], cols)
        pred = filter_violation_sql(oc[0], val) if oc else None
        if not pred:
            fchecks[col] = "n/a"
            continue
        try:
            bad = int(_scalar(con, closure_sql(graph, spec, f"SELECT COUNT(*) FROM {spec.name} WHERE {pred}"), timeout) or 0)
            fchecks[col] = "pass" if bad == 0 else "fail"
            if bad:
                rec["failures"].append(f"{bad} rows violate declared filter {col}={val}")
        except datasets.ExecError:
            fchecks[col] = "inconclusive"
    rec["filter_checks"] = fchecks
    rec["join_cardinality"] = join_cardinality(con, analyze_sql(spec.body_sql, [], spec.dialect).joins, timeout)
    if tests:
        rec["tests"] = run_tests(con, graph, spec, tests, timeout)
        for t in rec["tests"]:
            if t["result"] == "fail":
                rec["failures"].append(f"test failed ({t.get('purpose', '')}): {t['violations']} violating rows")
    rec["passed"] = not rec["failures"]
    return rec


def join_cardinality(con, joins: List[Dict[str, str]], timeout: float = ASSERT_TIMEOUT) -> List[Dict]:
    """Classify each equi-join by the uniqueness of its columns in the base tables (many_to_one is fan-out safe. many_to_many can inflate measures)."""
    out = []
    for j in joins[:6]:
        rec = {"join": f"{j['left_table']}.{j['left_col']}={j['right_table']}.{j['right_col']}"}
        uniq = []
        for t, c in ((j["left_table"], j["left_col"]), (j["right_table"], j["right_col"])):
            try:
                dup = _scalar(con, f"SELECT COUNT({q(c)}) - COUNT(DISTINCT {q(c)}) FROM {q(t)}", timeout)
                uniq.append(int(dup or 0) == 0)
            except (datasets.ExecError, Exception):  # noqa: BLE001  (a CTE/view side is not a base table)
                uniq.append(None)
        lu, ru = uniq
        rec["left_unique"], rec["right_unique"] = lu, ru
        if lu is None or ru is None:
            rec["relationship"] = "unknown"
        elif lu and ru:
            rec["relationship"] = "one_to_one"
        elif ru:
            rec["relationship"] = "many_to_one"
        elif lu:
            rec["relationship"] = "one_to_many"
        else:
            rec["relationship"] = "many_to_many"
        out.append(rec)
    return out


_UNSAFE_TEST = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace)\b", re.I)


def run_tests(con, graph, spec, tests: List[Dict], timeout: float = ASSERT_TIMEOUT) -> List[Dict]:
    """Execute generated test queries. Each returns ONE number: the count of violating rows (0 = pass). A test that does not execute is 'inconclusive' (the test may be wrong, the view is not blamed)."""
    out = []
    for t in tests[:4]:
        sql = str(t.get("sql", "")).strip().rstrip(";")
        rec = {"purpose": str(t.get("purpose", ""))[:200], "sql": sql[:800]}
        if not sql.lower().startswith("select") or ";" in sql or _UNSAFE_TEST.search(sql):
            rec.update(result="inconclusive", violations=None, error="not a single SELECT")
            out.append(rec)
            continue
        try:
            v = _scalar(con, closure_sql(graph, spec, sql), timeout)
            n = int(float(v)) if v is not None else 0
            rec.update(result="pass" if n == 0 else "fail", violations=n)
        except (datasets.ExecError, ValueError, TypeError) as e:
            rec.update(result="inconclusive", violations=None, error=str(e)[:200])
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# Full derivation (promotion) and completeness
# --------------------------------------------------------------------------- #
def lineage(graph: SkillRegistry, spec: ViewSpec) -> List[str]:
    """Base tables read by the view and, transitively, by its dependencies (view names are never lineage)."""
    views = {v.lower() for v in graph.views}
    seen, out, stack = set(), [], [spec]
    while stack:
        s = stack.pop()
        for t in s.source_tables or []:
            if t.lower() not in seen and t.lower() not in views:
                seen.add(t.lower())
                out.append(t)
        for d in s.depends_on or []:
            if d in graph.views and graph.views[d] is not s:
                stack.append(graph.views[d])
    return out


def derive(con, graph: SkillRegistry, spec: ViewSpec, scope: Scope, tests: Optional[List[Dict]] = None,
           timeout: float = ASSERT_TIMEOUT) -> Dict:
    """Derive the complete contract of `spec` (in place) from its SQL and the database, then validate it. `spec` must already be in `graph` so its closure resolves. Returns the validation record (also stored on spec.validation)."""
    import dataclasses
    old = dataclasses.replace(spec)
    spec.dialect = spec.dialect or scope.dialect
    facts = analyze_sql(spec.body_sql, list(graph.views), spec.dialect)
    try:
        outputs = output_columns(con, graph, spec)
    except Exception:  # noqa: BLE001
        outputs = []
    if outputs:
        spec.output_columns = outputs                     # what the view really returns
    if facts.parsed:
        # The SQL is authoritative, even when it reads only other views (then there are no base tables here: the model's self-reported source_tables often names the dependency view).
        spec.source_tables = list(facts.base_tables)
        spec.depends_on = list(dict.fromkeys([d for d in spec.depends_on if d in graph.views] +
                                             [d for d in facts.view_refs if d in graph.views and d != spec.name]))
        merged = dict(spec.semantic_filters or {})
        merged.update(facts.filters)                      # SQL is authoritative for the columns it filters
        # Effective contract: a view that reads a filtered dependency is restricted by that filter too (cohorts and time windows propagate). Dependencies are derived first, so their filters are already effective.
        inherited = {}
        for d in spec.depends_on:
            for k, v in ((graph.views[d].semantic_filters or {}).items() if d in graph.views else ()):
                if norm_key(k) not in {norm_key(x) for x in merged}:
                    merged[k] = v
                    inherited[str(k)] = str(v)
        spec.semantic_filters = {str(k): str(v) for k, v in merged.items()}
        if inherited:
            spec.provenance["inherited_filters"] = inherited
        spec.aggregation = facts.aggregation
        spec.join_keys = [f"{j['left_table']}.{j['left_col']}={j['right_table']}.{j['right_col']}"
                          for j in facts.joins]
    try:
        rc = int(_scalar(con, closure_sql(graph, spec, f"SELECT COUNT(*) FROM {spec.name}"), timeout) or 0)
    except datasets.ExecError:
        rc = None
    if facts.parsed and outputs:
        kind, grain, basis = derive_grain(con, graph, spec, facts, outputs, rc, timeout)
    else:
        kind, grain, basis = GRAIN_UNKNOWN, [], "unparsed"
    spec.grain_kind, spec.grain = kind, grain
    lin = lineage(graph, spec)
    rel_prov = relational_provenance(con, graph, spec, facts, outputs)
    spec.provenance.update({
        "contract_version": CONTRACT_VERSION, "grain_basis": basis, "lineage": lin,
        **rel_prov,
        "table_fingerprints": {t.lower(): scope.table_fp.get(t.lower(), "") for t in lin},
        # an observed (not guaranteed) grain is only trusted for the data it was checked on
        "data_fingerprints": ({t.lower(): scope.data_fp.get(t.lower(), "") for t in lin}
                              if basis in DATA_DERIVED_GRAIN else {}),
        "db_id": scope.db_id,
    })
    spec.sql_hash = sql_hash(spec, graph)
    spec.skill_id = skill_id_for(spec.sql_hash)
    rec = validate(con, graph, spec, timeout, tests)
    spec.validation = rec
    if spec.name in graph.views:
        graph.reindex(spec.name, old)
    return rec


def completeness(spec: ViewSpec) -> List[str]:
    """Reasons the contract is NOT complete enough for automatic reuse (empty list = complete)."""
    why = []
    if not spec.output_columns:
        why.append("unknown outputs")
    if spec.grain_kind not in (GRAIN_SCALAR, GRAIN_KEYED):
        why.append("unknown grain")
    elif spec.grain_kind == GRAIN_KEYED:
        outs = {norm_key(o) for o in spec.output_columns}
        if not spec.grain or not {norm_key(g) for g in spec.grain} <= outs:
            why.append("grain keys not exposed")
    if not (spec.validation or {}).get("passed"):
        why.append("validation not passed")
    if int((spec.provenance or {}).get("contract_version", 0) or 0) < CONTRACT_VERSION:
        why.append("legacy contract")
    if not spec.sql_hash:
        why.append("no identity")
    return why


def contract_signature(spec: ViewSpec) -> Tuple:
    """Structural contract used to detect equivalent / conflicting / subsuming skills."""
    return (spec.category, spec.grain_kind,
            frozenset(norm_key(g) for g in spec.grain or []),
            frozenset(norm_key(o) for o in spec.output_columns or []),
            tuple(sorted((norm_key(k), str(v).strip().lower()) for k, v in (spec.semantic_filters or {}).items())),
            frozenset(t.lower() for t in (spec.provenance or {}).get("lineage", spec.source_tables or [])))


def provenance_signature(spec: ViewSpec) -> Tuple:
    """Canonical structural signature for provenance-aware equivalence checks."""
    prov = spec.provenance or {}
    output_lineage = prov.get("output_lineage") or {}

    def join_key(key):
        sides = str(key).split("=", 1)
        return tuple(sorted(norm_key(side) for side in sides))

    return (
        tuple(prov.get("operators") or []),
        frozenset(norm_key(c) for c in prov.get("source_columns") or []),
        tuple(sorted((norm_key(out), tuple(sorted(norm_key(c) for c in cols)))
                     for out, cols in output_lineage.items())),
        tuple(sorted(join_key(k) for k in spec.join_keys or [])),
        tuple(sorted((norm_key(k), norm_key(v))
                     for k, v in (prov.get("parameter_bindings") or {}).items())),
    )


def result_signature(con, graph: SkillRegistry, spec: ViewSpec, cap: int = 20000,
                     timeout: float = ASSERT_TIMEOUT) -> Optional[str]:
    """Order-insensitive hash of the view's full result (None when larger than `cap` rows or not executable)."""
    try:
        rows = datasets.run_sql(con, closure_sql(graph, spec, f"SELECT * FROM {spec.name} LIMIT {cap + 1}"), timeout)
    except datasets.ExecError:
        return None
    if len(rows) > cap:
        return None
    canon = sorted(tuple(str(round(x, 6) if isinstance(x, float) else x) for x in r) for r in rows)
    return hashlib.sha1(json.dumps(canon).encode()).hexdigest()


__all__ = ["Scope", "make_scope", "table_fingerprint", "schema_fingerprint", "normalize_sql", "sql_hash",
           "skill_id_for", "analyze_sql", "derive", "validate", "completeness", "contract_signature",
           "result_signature", "interval_contains", "parse_interval", "is_range", "closure_sql", "lineage",
           "provenance_signature", "relational_provenance", "GRAIN_SCALAR", "GRAIN_KEYED",
           "GRAIN_UNKNOWN", "CONTRACT_VERSION", "DECOMPOSABLE"]
