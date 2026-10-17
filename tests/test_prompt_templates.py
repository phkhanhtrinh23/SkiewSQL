import ast
from pathlib import Path

import pytest

from skiewsql.prompt_loader import load_prompt


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skiewsql"
TEMPLATE_ROOT = ROOT / "templates"
MAINTAINED_PROMPT_MODULES = (
    "agents.py",
    "beaver_method.py",
    "science_method.py",
    "sf_method.py",
    "skillify.py",
    "spider2sf.py",
    "table_catalog.py",
)


def test_templates_are_external_and_loadable():
    templates = sorted(TEMPLATE_ROOT.glob("*/*.txt"))
    assert len(templates) >= 70
    for path in templates:
        relative = path.relative_to(TEMPLATE_ROOT).as_posix()
        assert load_prompt(relative) == path.read_text(encoding="utf-8")


def test_prompt_constants_are_loader_calls_not_embedded_bodies():
    for filename in MAINTAINED_PROMPT_MODULES:
        tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            is_prompt = (name.endswith(("_SYS", "_USER", "_RULES", "_PROMPT"))
                         and name not in {"MYSQL_USER", "PG_USER"})
            is_fragment = name in {
                "CAT_HELP", "REWRITE_USER_NOSCHEMA", "QUALIFY_OUTPUTS_RULE",
                "QUALIFY_SEED_OUTPUTS", "EXISTING_VIEWS",
                "DEPENDENCY_CONTRACT", "VALUE_HINTS", "PRIOR_ERROR",
            }
            if is_prompt or is_fragment:
                assert isinstance(node.value, ast.Call), f"embedded prompt: {filename}:{name}"
                assert isinstance(node.value.func, ast.Name)
                assert node.value.func.id == "load_prompt"


@pytest.mark.parametrize("bad_path", ("../secret.txt", "/tmp/prompt.txt", "agents/rewrite_sys.md"))
def test_prompt_loader_rejects_unsafe_or_non_text_paths(bad_path):
    with pytest.raises(ValueError):
        load_prompt(bad_path)
