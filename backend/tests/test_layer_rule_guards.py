"""Exercise target rules through real temporary Python files, without app imports."""

from pathlib import Path

import pytest

from tests.layer_rules import ImportEdge, forbidden, imports_in, violations


@pytest.mark.parametrize(
    ("source", "statement", "target"),
    [
        (
            "domain/station/model.py",
            "import app.application.station",
            "app.application.station",
        ),
        (
            "domain/station/model.py",
            "from ... import infrastructure",
            "app.infrastructure",
        ),
        (
            "domain/station/model.py",
            "from ...application import station",
            "app.application.station",
        ),
        ("domain/station/model.py", "from fastapi import FastAPI", "fastapi.FastAPI"),
        ("domain/station/model.py", "from boto3 import client", "boto3.client"),
        ("domain/station/model.py", "import pydantic", "pydantic"),
        (
            "domain/station/new_port.py",
            "from typing import Protocol",
            "typing.Protocol",
        ),
        (
            "application/station/example.py",
            "from ...infrastructure import database",
            "app.infrastructure.database",
        ),
        ("application/station/example.py", "from ... import di", "app.di"),
        ("application/station/example.py", "from app import config", "app.config"),
        ("application/station/example.py", "import fastapi", "fastapi"),
        ("application/station/example.py", "import boto3", "boto3"),
        ("application/station/example.py", "import pydantic", "pydantic"),
        ("application/station/example.py", "import httpx", "httpx"),
        (
            "presentation/api/stations/example.py",
            (
                "from ....application.station.list_station_use_case "
                "import ListStationUseCase"
            ),
            "app.application.station.list_station_use_case.ListStationUseCase",
        ),
        (
            "presentation/api/stations/example.py",
            (
                "from app.application.station.ports.outbound.repository "
                "import StationRepository"
            ),
            "app.application.station.ports.outbound.repository.StationRepository",
        ),
        (
            "presentation/api/stations/example.py",
            "from app.di.container import get_station_use_case",
            "app.di.container.get_station_use_case",
        ),
        (
            "presentation/api/stations/example.py",
            "from ....domain.station import model",
            "app.domain.station.model",
        ),
        (
            "presentation/api/stations/example.py",
            "from ....infrastructure import database",
            "app.infrastructure.database",
        ),
        (
            "infrastructure/repositories/example.py",
            (
                "from ...application.station.list_station_use_case "
                "import ListStationUseCase"
            ),
            "app.application.station.list_station_use_case.ListStationUseCase",
        ),
        (
            "infrastructure/repositories/example.py",
            (
                "from app.application.station.ports.inbound.list_station "
                "import ListStationPort"
            ),
            "app.application.station.ports.inbound.list_station.ListStationPort",
        ),
        (
            "infrastructure/repositories/example.py",
            "from ... import presentation",
            "app.presentation",
        ),
        ("infrastructure/repositories/example.py", "from ... import di", "app.di"),
        (
            "di/container.py",
            "from ..presentation.api.stations import get_stations",
            "app.presentation.api.stations.get_stations",
        ),
        ("di/container.py", "from .. import main", "app.main"),
        (
            "main.py",
            "from app.infrastructure.seed import seed_and_migrate",
            "app.infrastructure.seed.seed_and_migrate",
        ),
        (
            "handler.py",
            "from .infrastructure.seed import seed_and_migrate",
            "app.infrastructure.seed.seed_and_migrate",
        ),
    ],
)
def test_forbidden_import_in_real_file_is_detected(
    tmp_path: Path, source: str, statement: str, target: str
) -> None:
    app_dir = tmp_path / "app"
    path = app_dir / source
    path.parent.mkdir(parents=True)
    path.write_text(statement + "\n")

    assert violations(app_dir) == {ImportEdge(source, target)}


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("domain/station/model.py", "datetime.date"),
        ("domain/temperature/input_policy.py", "app.domain.station.model.Station"),
        (
            "application/station/list_station_use_case.py",
            "app.application.station.ports.inbound.list_station.ListStationPort",
        ),
        ("application/temperature/fetch_month_use_case.py", "asyncio.timeout"),
        (
            "application/temperature/get_temperature_use_case.py",
            "app.application.shared.ports.outbound.clock.Clock",
        ),
        (
            "presentation/api/stations/get_stations.py",
            "app.application.station.ports.inbound.list_station.ListStationPort",
        ),
        (
            "presentation/api/stations/get_stations.py",
            "app.application.station.ports.inbound",
        ),
        ("presentation/api/stations/get_stations.py", "fastapi.Depends"),
        (
            "infrastructure/repositories/station_repository.py",
            "app.application.station.ports.outbound.repository.StationRepository",
        ),
        (
            "infrastructure/repositories/station_repository.py",
            "app.domain.station.model.Station",
        ),
        ("infrastructure/repositories/station_repository.py", "boto3.resource"),
        (
            "di/container.py",
            "app.application.station.list_station_use_case.ListStationUseCase",
        ),
        (
            "di/container.py",
            (
                "app.infrastructure.repositories.station_repository."
                "DynamoDBStationRepository"
            ),
        ),
        ("di/container.py", "app.presentation.api.shared.dependencies.station_port"),
        ("main.py", "app.di.container.register_dependencies"),
        ("handler.py", "app.main.app"),
    ],
)
def test_valid_target_dependencies_remain_allowed(source: str, target: str) -> None:
    assert not forbidden(ImportEdge(source, target))


def test_relative_init_and_aliased_imports_are_resolved(tmp_path: Path) -> None:
    app_dir = tmp_path / "app"
    path = app_dir / "presentation/api/stations/__init__.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "from . import get_stations as route\n"
        "from .... import infrastructure as infra\n"
        "import app.application.station as station\n"
    )
    assert imports_in(path, app_dir) == {
        ImportEdge(
            "presentation/api/stations/__init__.py",
            "app.presentation.api.stations.get_stations",
        ),
        ImportEdge("presentation/api/stations/__init__.py", "app.infrastructure"),
        ImportEdge("presentation/api/stations/__init__.py", "app.application.station"),
    }


@pytest.mark.parametrize(
    "statement",
    [
        "from typing import Protocol\nclass NewPort(Protocol): pass",
        "import typing as t\nclass NewPort(t.Protocol): pass",
        "from typing import Protocol as P\nclass NewPort(P): pass",
        "from typing import Protocol as P\nclass NewPort(P[T]): pass",
    ],
)
def test_domain_protocol_definition_cannot_hide_behind_alias(
    tmp_path: Path, statement: str
) -> None:
    from tests.layer_rules import domain_protocols

    app_dir = tmp_path / "app"
    path = app_dir / "domain/station/new_port.py"
    path.parent.mkdir(parents=True)
    path.write_text(statement)
    assert domain_protocols(app_dir) == {("domain/station/new_port.py", "NewPort")}
