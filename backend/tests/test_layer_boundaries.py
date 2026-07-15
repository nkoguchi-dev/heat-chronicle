import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _imports_under(directory: Path) -> set[str]:
    imports: set[str] = set()
    for path in directory.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module)
    return imports


def test_domain_and_application_do_not_depend_on_pydantic() -> None:
    imports = _imports_under(APP_DIR / "domain") | _imports_under(
        APP_DIR / "application"
    )

    assert not any(
        name == "pydantic" or name.startswith("pydantic.") for name in imports
    )


def test_domain_files_are_grouped_by_resource() -> None:
    root_python_files = {path.name for path in (APP_DIR / "domain").glob("*.py")}

    assert root_python_files == {"__init__.py"}


def test_application_only_depends_on_domain_layer() -> None:
    imports = _imports_under(APP_DIR / "application")
    project_imports = {name for name in imports if name.startswith("app.")}

    assert all(name.startswith("app.domain") for name in project_imports)


def test_domain_does_not_depend_on_outer_layers() -> None:
    imports = _imports_under(APP_DIR / "domain")
    project_imports = {name for name in imports if name.startswith("app.")}

    assert all(name.startswith("app.domain") for name in project_imports)


def test_infrastructure_does_not_depend_on_outer_layers() -> None:
    imports = _imports_under(APP_DIR / "infrastructure")
    forbidden_prefixes = (
        "app.application",
        "app.presentation",
        "app.di",
    )

    assert not any(name.startswith(forbidden_prefixes) for name in imports)


def test_presentation_does_not_depend_on_infrastructure() -> None:
    imports = _imports_under(APP_DIR / "presentation")

    assert not any(name.startswith("app.infrastructure") for name in imports)


def test_infrastructure_dto_does_not_leak_to_upper_layers() -> None:
    imports = (
        _imports_under(APP_DIR / "domain")
        | _imports_under(APP_DIR / "application")
        | _imports_under(APP_DIR / "presentation")
    )

    assert not any(name.startswith("app.infrastructure.dto") for name in imports)


def test_presentation_dto_does_not_leak_to_other_layers() -> None:
    imports = (
        _imports_under(APP_DIR / "domain")
        | _imports_under(APP_DIR / "application")
        | _imports_under(APP_DIR / "infrastructure")
    )

    assert not any(name.startswith("app.presentation") for name in imports)
