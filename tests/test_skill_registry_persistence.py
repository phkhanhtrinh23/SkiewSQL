from pathlib import Path

from skiewsql import sqlview
from skiewsql.core import SkillRegistry, ViewSpec
from skiewsql.visualize_registry import render_registry


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


def test_save_reload_and_render_complete_skill_registry(tmp_path: Path):
    registry = SkillRegistry("example_db")
    registry.add_view(_spec("base"))
    registry.add_view(_spec("joined", category="JOIN", depends_on=["base"]))

    registry_path = tmp_path / "registry.json"
    sqlview.save_registry(registry, str(registry_path))

    markdown = registry_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "Which active entity has id 1?" in markdown
    assert "Count inactive entities." in markdown
    assert '"when_to_use": "active entity questions"' in markdown
    assert '"status": "active"' in markdown
    assert "SELECT 1 AS id" in markdown

    loaded = sqlview.load_registry(str(registry_path))
    assert loaded.n_views() == 2
    assert loaded.n_edges("READS_TABLE") == 2
    assert loaded.check_consistency() == []
    assert loaded.n_edges("DEPENDS_ON") == 1
    assert loaded.views["joined"].depends_on == ["base"]

    figure = render_registry(
        str(registry_path), str(tmp_path / "focused.png"), focus=["joined"],
        highlight=["joined"], title="Focused test registry", dpi=80,
    )
    assert figure.exists()
    assert figure.stat().st_size > 0
