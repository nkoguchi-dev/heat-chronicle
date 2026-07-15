import ast
import re
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


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id == "dataclass":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "dataclass":
            return True
    return False


def _to_snake_case(name: str) -> str:
    with_word_boundaries = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", with_word_boundaries).lower()


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


def test_application_files_are_grouped_by_feature() -> None:
    root_python_files = {path.name for path in (APP_DIR / "application").glob("*.py")}

    assert root_python_files == {"__init__.py"}


def test_application_behavior_classes_follow_naming_rules() -> None:
    violations: dict[str, str] = {}
    application_dir = APP_DIR / "application"
    for path in application_dir.rglob("*.py"):
        relative_path = path.relative_to(application_dir)
        is_shared = relative_path.parts[0] == "shared"
        expected_suffix = "Service" if is_shared else "UseCase"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or _is_dataclass(node):
                continue
            expected_file = f"{_to_snake_case(node.name)}.py"
            if not node.name.endswith(expected_suffix) or path.name != expected_file:
                violations[f"{relative_path}:{node.name}"] = (
                    f"expected {expected_suffix} class in {expected_file}"
                )

    assert violations == {}


def test_application_use_case_has_at_most_one_public_method() -> None:
    violations: dict[str, list[str]] = {}
    for path in (APP_DIR / "application").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not node.name.endswith("UseCase"):
                continue
            public_methods = [
                member.name
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not member.name.startswith("_")
            ]
            if len(public_methods) > 1:
                violations[f"{path.relative_to(APP_DIR)}:{node.name}"] = public_methods

    assert violations == {}


def test_application_outputs_do_not_reference_domain_types() -> None:
    violations: dict[str, list[str]] = {}
    for path in (APP_DIR / "application").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        domain_names = {
            alias.asname or alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("app.domain")
            for alias in node.names
        }

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            annotations: list[ast.expr] = []
            if node.name.endswith("Output"):
                annotations.extend(
                    member.annotation
                    for member in node.body
                    if isinstance(member, ast.AnnAssign)
                )
            if node.name.endswith("UseCase"):
                for member in node.body:
                    if (
                        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not member.name.startswith("_")
                        and member.returns is not None
                    ):
                        annotations.append(member.returns)

            referenced_names = {
                child.id
                for annotation in annotations
                for child in ast.walk(annotation)
                if isinstance(child, ast.Name)
            }
            leaked_names = sorted(domain_names & referenced_names)
            if leaked_names:
                violations[f"{path.relative_to(APP_DIR)}:{node.name}"] = leaked_names

    assert violations == {}


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


def test_presentation_does_not_call_application_shared_directly() -> None:
    imports = _imports_under(APP_DIR / "presentation")

    assert not any(name.startswith("app.application.shared") for name in imports)


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
