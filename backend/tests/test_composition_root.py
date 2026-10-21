from pathlib import Path
from unittest.mock import patch

import pytest

from app.di.lifecycle import initialize_host, initialize_lambda
from tests.layer_rules import concrete_connections


def test_host_initializes_tables_before_seed() -> None:
    calls: list[str] = []
    with (
        patch(
            "app.di.lifecycle.ensure_tables_exist",
            side_effect=lambda: calls.append("tables"),
        ),
        patch(
            "app.di.lifecycle.seed_and_migrate",
            side_effect=lambda: calls.append("seed"),
        ),
    ):
        initialize_host()
    assert calls == ["tables", "seed"]


def test_lambda_preserves_seed_only_initialization() -> None:
    with (
        patch("app.di.lifecycle.ensure_tables_exist") as tables,
        patch("app.di.lifecycle.seed_and_migrate") as seed,
    ):
        initialize_lambda()
    tables.assert_not_called()
    seed.assert_called_once_with()


@pytest.mark.parametrize(
    "statement",
    [
        (
            "from app.application.station.list_station_use_case "
            "import ListStationUseCase as UC\nUC(None)"
        ),
        (
            "import app.infrastructure.scraper.jma_client as client\n"
            "client.JmaClient(None)"
        ),
        "from ...infrastructure.scraper.jma_client import JmaClient\nJmaClient(None)",
    ],
)
def test_constructor_outside_di_is_detected(tmp_path: Path, statement: str) -> None:
    app_dir = tmp_path / "app"
    path = app_dir / "application/station/probe.py"
    path.parent.mkdir(parents=True)
    path.write_text(statement)
    assert len(concrete_connections(app_dir)) == 1
