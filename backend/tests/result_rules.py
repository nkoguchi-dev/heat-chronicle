"""Narrow guards for the migrated business-result boundaries, not all raises."""

import ast
from pathlib import Path

LEGACY_FAILURES = {
    "PrefectureNotFound",
    "StationNotFound",
    "InvalidTemperatureInput",
    "FetchUnavailable",
}


def result_control_violations(source: str, path: str) -> set[str]:
    tree = ast.parse(source, filename=path)
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module or ''}.{alias.name}"

    def leaf(node: ast.expr) -> str:
        value = node.func if isinstance(node, ast.Call) else node
        name = ast.unparse(value)
        head, *tail = name.split(".")
        return ".".join([names.get(head, head), *tail]).split(".")[-1]

    internal = (
        path.startswith("application/") or path == "domain/temperature/input_policy.py"
    )
    endpoint = any(
        path.startswith(f"presentation/api/{resource}/")
        for resource in ("stations", "temperature", "prefectures")
    )
    result: set[str] = set()
    for node in ast.walk(tree):
        if internal and isinstance(node, ast.ClassDef):
            if any(
                leaf(base)
                in {"Exception", "ValueError", "RuntimeError", *LEGACY_FAILURES}
                for base in node.bases
            ):
                result.add(f"{path}:{node.lineno}: business exception class")
        if isinstance(node, ast.Raise) and node.exc is not None:
            target = leaf(node.exc)
            if internal and target in {"ValueError", *LEGACY_FAILURES}:
                result.add(f"{path}:{node.lineno}: expected failure raised")
            if endpoint and target == "HTTPException":
                result.add(f"{path}:{node.lineno}: HTTP exception raised")
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            types = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            if (internal or endpoint) and any(
                leaf(item)
                in {"Exception", "RuntimeError", "ValueError", *LEGACY_FAILURES}
                for item in types
            ):
                result.add(f"{path}:{node.lineno}: broad or business exception caught")
        if endpoint and isinstance(node, ast.ImportFrom):
            if any(
                leaf(ast.Name(id=alias.asname or alias.name)) == "HTTPException"
                for alias in node.names
            ):
                result.add(f"{path}:{node.lineno}: HTTP exception imported")
    return result


def result_violations(app_dir: Path) -> set[str]:
    return {
        violation
        for path in app_dir.rglob("*.py")
        for violation in result_control_violations(
            path.read_text(), path.relative_to(app_dir).as_posix()
        )
    }
