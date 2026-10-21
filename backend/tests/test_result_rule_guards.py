import subprocess
import sys
from pathlib import Path

import pytest

from tests.result_rules import result_control_violations, result_violations


@pytest.mark.parametrize(
    "source,path",
    [
        (
            (
                (
                    "from fastapi import HTTPException as Fail\n"
                    "def endpoint():\n"
                    "    raise Fail(404)"
                )
            ),
            "presentation/api/stations/get_stations.py",
        ),
        (
            (
                "import fastapi as api\n"
                "def endpoint():\n"
                "    raise api.HTTPException(404)"
            ),
            "presentation/api/temperature/fetch_month.py",
        ),
        (
            "class Missing(ValueError): pass",
            "application/station/ports/inbound/list_station.py",
        ),
        (
            ("def use_case():\n" "    raise ValueError('missing')"),
            "application/station/list_station_use_case.py",
        ),
        (
            (
                (
                    "from .errors import FetchUnavailable as Busy\n"
                    "def use_case():\n"
                    "    raise Busy()"
                )
            ),
            "application/temperature/fetch_month_use_case.py",
        ),
        (
            (
                (
                    "def use_case():\n"
                    "    try: work()\n"
                    "    except (TimeoutError, RuntimeError): return 'unavailable'"
                )
            ),
            "application/temperature/fetch_month_use_case.py",
        ),
        (
            (
                "def use_case():\n"
                "    try: work()\n"
                "    except Exception: return 'missing'"
            ),
            "application/station/list_station_use_case.py",
        ),
        (
            (
                (
                    "import builtins as b\n"
                    "def use_case():\n"
                    "    try: work()\n"
                    "    except b.ValueError: return 'missing'"
                )
            ),
            "application/station/list_station_use_case.py",
        ),
        (
            "class InvalidTemperatureInput(ValueError): pass",
            "domain/temperature/input_policy.py",
        ),
    ],
)
def test_business_exception_regressions_are_detected(source: str, path: str) -> None:
    assert result_control_violations(source, path)


@pytest.mark.parametrize(
    "source,path",
    [
        (
            ("def adapter():\n" "    try: sdk()\n" "    except ClientError: raise"),
            "infrastructure/repositories/station_repository.py",
        ),
        (
            ("def validator():\n" "    raise ValueError('invalid external payload')"),
            "infrastructure/dto/station.py",
        ),
        (
            (
                (
                    "async def use_case():\n"
                    "    try: await refresh()\n"
                    "    except TimeoutError: return Unavailable()"
                )
            ),
            "application/temperature/fetch_month_use_case.py",
        ),
        (
            ("def provider():\n" "    raise RuntimeError('provider not registered')"),
            "presentation/api/shared/dependencies.py",
        ),
        (
            (
                (
                    "async def handler():\n"
                    "    try: await route()\n"
                    "    except Exception: return error_response()"
                )
            ),
            "presentation/api/shared/internal_server_error.py",
        ),
        (
            (
                (
                    "async def use_case():\n"
                    "    try: await release()\n"
                    "    except BaseException:\n"
                    "        if no_active_error: raise"
                )
            ),
            "application/temperature/fetch_month_use_case.py",
        ),
        (
            (
                (
                    "def use_case(result):\n"
                    "    match result:\n"
                    "        case Missing(): return NotFound()\n"
                    "        case Found(value=value): return value\n"
                    "        case other: assert_never(other)"
                )
            ),
            "application/station/list_station_use_case.py",
        ),
    ],
)
def test_legitimate_exception_boundaries_are_allowed(source: str, path: str) -> None:
    assert result_control_violations(source, path) == set()


def test_application_result_boundaries_have_no_exception_control_debt() -> None:
    assert result_violations(Path(__file__).resolve().parents[1] / "app") == set()


def test_mypy_detects_an_unhandled_result_variant(tmp_path: Path) -> None:
    snippet = tmp_path / "result_exhaustiveness.py"
    source = """from dataclasses import dataclass
from typing import assert_never
@dataclass(frozen=True)
class Found: pass
@dataclass(frozen=True)
class Missing: pass
@dataclass(frozen=True)
class StorageUnavailable: pass
def handle(result: Found | Missing) -> str:
    match result:
        case Found(): return "ok"
        case Missing(): return "missing"
        case unexpected: assert_never(unexpected)
"""
    snippet.write_text(source)
    command = [
        sys.executable,
        "-m",
        "mypy",
        "--strict",
        "--no-incremental",
        str(snippet),
    ]
    complete = subprocess.run(command, capture_output=True, text=True, check=False)
    assert complete.returncode == 0, complete.stdout + complete.stderr
    snippet.write_text(
        source.replace(
            "result: Found | Missing", "result: Found | Missing | StorageUnavailable"
        )
    )
    incomplete = subprocess.run(command, capture_output=True, text=True, check=False)
    assert incomplete.returncode == 1
    assert (
        "assert_never" in incomplete.stdout
        and "StorageUnavailable" in incomplete.stdout
    )


def test_endpoint_value_error_to_response_regression_is_detected() -> None:
    source = (
        "def endpoint():\n"
        "    try: work()\n"
        "    except ValueError: return JSONResponse(status_code=404)"
    )
    assert result_control_violations(
        source, "presentation/api/temperature/get_temperature.py"
    )
