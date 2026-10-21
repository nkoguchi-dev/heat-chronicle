"""Static import boundaries; migration exceptions are exact (file, target) pairs."""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class ImportEdge:
    source: str
    target: str


def imports_in(path: Path, app_dir: Path) -> set[ImportEdge]:
    relative = path.relative_to(app_dir)
    package = ("app", *relative.parts[:-1])
    edges: set[ImportEdge] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                if node.level > len(package):
                    raise ValueError(f"Import escapes package: {relative}")
                base = ".".join((*package[: len(package) - node.level + 1], base))
                base = base.rstrip(".")
            targets = [f"{base}.{alias.name}" for alias in node.names]
        else:
            continue
        edges.update(ImportEdge(relative.as_posix(), target) for target in targets)
    return edges


def under(target: str, prefix: str) -> bool:
    return target == prefix or target.startswith(prefix + ".")


def port_target(target: str, direction: str) -> bool:
    parts = target.split(".")
    return (
        len(parts) >= 5
        and parts[:2] == ["app", "application"]
        and parts[3:5] == ["ports", direction]
    )


def forbidden(edge: ImportEdge) -> bool:
    """Target rules, independent of the currently accepted migration debt."""
    source, target = edge.source, edge.target
    layer = source.split("/")[0]
    is_project = under(target, "app")
    if layer == "domain":
        if target == "typing.Protocol":
            return True  # Domain has no external I/O Protocol after migration.
        return (
            not under(target, "app.domain")
            if is_project
            else target.split(".")[0] not in sys.stdlib_module_names
        )
    if layer == "application":
        return (
            not any(
                under(target, prefix) for prefix in ("app.application", "app.domain")
            )
            if is_project
            else target.split(".")[0] not in sys.stdlib_module_names
        )
    if layer == "presentation" and is_project:
        return not (under(target, "app.presentation") or port_target(target, "inbound"))
    if layer == "infrastructure" and is_project:
        return not (
            any(
                under(target, prefix)
                for prefix in ("app.infrastructure", "app.domain", "app.config")
            )
            or port_target(target, "outbound")
        )
    if layer == "di" and is_project:
        return not (
            any(
                under(target, prefix)
                for prefix in (
                    "app.application",
                    "app.domain",
                    "app.infrastructure",
                    "app.di",
                    "app.config",
                )
            )
            or under(target, "app.presentation.api.shared.dependencies")
        )
    if source == "main.py" and is_project:
        return not any(
            under(target, prefix)
            for prefix in ("app.di", "app.presentation", "app.config")
        )
    if source == "handler.py" and is_project:
        return not any(under(target, prefix) for prefix in ("app.main", "app.di"))
    return False


def violations(app_dir: Path) -> set[ImportEdge]:
    return {
        edge
        for path in app_dir.rglob("*.py")
        for edge in imports_in(path, app_dir)
        if forbidden(edge)
    }


# Baseline at #154. Remove each pair in its migration PR; never regenerate to
# accept new violations. Stale exceptions also fail the boundary test.
MIGRATION_EXCEPTIONS: set[ImportEdge] = {
    ImportEdge("domain/temperature/data_source.py", "typing.Protocol"),
    ImportEdge("domain/temperature/fetch_guard.py", "typing.Protocol"),
    ImportEdge("handler.py", "app.infrastructure.seed.seed_and_migrate"),
    ImportEdge("main.py", "app.infrastructure.init_tables.ensure_tables_exist"),
    ImportEdge("main.py", "app.infrastructure.seed.seed_and_migrate"),
    ImportEdge(
        "presentation/api/temperature/fetch_month.py",
        "app.di.container.FetchMonthUseCaseDep",
    ),
    ImportEdge(
        "presentation/api/temperature/fetch_month.py",
        "app.domain.temperature.fetch_guard.FetchUnavailable",
    ),
    ImportEdge(
        "presentation/api/temperature/fetch_month.py",
        "app.domain.temperature.input_policy.InvalidTemperatureInput",
    ),
}


def domain_protocols(app_dir: Path) -> set[tuple[str, str]]:
    """Find Protocol definitions even when typing/Protocol is imported by alias."""
    result: set[tuple[str, str]] = set()
    for path in (app_dir / "domain").rglob("*.py"):
        tree = ast.parse(path.read_text())
        names: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                value = base.value if isinstance(base, ast.Subscript) else base
                name = ast.unparse(value)
                head, *tail = name.split(".")
                resolved = ".".join([names.get(head, head), *tail])
                if resolved in {"typing.Protocol", "typing_extensions.Protocol"}:
                    result.add((path.relative_to(app_dir).as_posix(), node.name))
    return result


# Delete these definitions and entries together in #156 / #157 / #158.
DOMAIN_PROTOCOL_EXCEPTIONS = {
    ("domain/temperature/data_source.py", "TemperatureDataSource"),
    ("domain/temperature/fetch_guard.py", "FetchGuard"),
}
