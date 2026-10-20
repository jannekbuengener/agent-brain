import importlib
import tomllib


SCAFFOLD_MODULES = (
    "agent_brain",
    "agent_brain.core",
    "agent_brain.retrieval",
    "agent_brain.memory",
    "agent_brain.surrealdb",
    "agent_brain.connectors",
)


def test_scaffold_module_boundaries_are_importable() -> None:
    for module_name in SCAFFOLD_MODULES:
        module = importlib.import_module(module_name)
        assert module.__name__ == module_name


def test_scaffold_has_no_runtime_dependencies(repo_root) -> None:
    with (repo_root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["requires-python"] == ">=3.12"
    assert project["dependencies"] == []
