from pathlib import Path

from skiewsql import sqlview
from skiewsql.core import ViewGraph, ViewSpec
from skiewsql.visualize_skill_graph import render_graph


def _spec(name: str, *, category: str = "NORM", depends_on=None) -> ViewSpec:
    return ViewSpec(
        name=name,
        category=category,
        body_sql="SELECT 1 AS id",
        source_tables=["source_table"],
        output_columns=["id"],
        grain=["id"],
        semantic_filters={"status": "active"},
        depends_on=list(depends_on or []),
        params={"when_to_use": "active entity questions"},
        description=f"Reusable relation {name}",
        validated_on=["Which active entity has id 1?"],
        counter_examples=["Count inactive entities."],
    )


def test_save_reload_and_render_complete_skill_graph(tmp_path: Path):
    graph = ViewGraph("example_db")
    graph.add_view(_spec("base"))
    graph.add_view(_spec("joined", category="JOIN", depends_on=["base"]))

    graph_path = tmp_path / "graph.json"
    sqlview.save_graph(graph, str(graph_path))

    markdown = graph_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "Which active entity has id 1?" in markdown
    assert "Count inactive entities." in markdown
    assert '"when_to_use": "active entity questions"' in markdown
    assert '"status": "active"' in markdown
    assert "SELECT 1 AS id" in markdown

    loaded = sqlview.load_graph(str(graph_path))
    assert loaded.n_views() == 2
    assert loaded.n_edges("READS_TABLE") == 2
    assert loaded.check_consistency() == []
    assert loaded.n_edges("DEPENDS_ON") == 1
    assert loaded.g.has_edge("view::joined", "view::base")

    figure = render_graph(
        str(graph_path), str(tmp_path / "focused.png"), focus=["joined"],
        highlight=["joined"], title="Focused test graph", dpi=80,
    )
    assert figure.exists()
    assert figure.stat().st_size > 0
