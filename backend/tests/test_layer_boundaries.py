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
