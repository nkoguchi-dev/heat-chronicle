from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.di.container import (
    get_station_repository,
    get_temperature_data_source,
    get_temperature_repository,
)
from app.infrastructure.repositories.station_repository import (
    DynamoDBStationRepository,
)
from app.infrastructure.repositories.temperature_repository import (
    DynamoDBTemperatureRepository,
)
from app.main import app
from integration_tests.fixtures.mock_overrides import MockTemperatureDataSource


@asynccontextmanager
async def _noop_lifespan(application: Any) -> AsyncGenerator[None, None]:
    """lifespan を無効化する（ensure_tables_exist / seed_and_migrate をスキップ）。"""
    yield


@pytest.fixture
async def client(
    dynamodb_resource: Any,
    test_settings: Settings,
    mock_temperature_data_source: MockTemperatureDataSource,
) -> AsyncGenerator[AsyncClient, None]:
    """テストごとに新しい AsyncClient を作成する。
    DI をオーバーライドしてテスト用 DynamoDB を注入し、lifespan を無効化する。
    """
    app.router.lifespan_context = _noop_lifespan

    app.dependency_overrides[get_station_repository] = (
        lambda: DynamoDBStationRepository(dynamodb_resource)
    )
    app.dependency_overrides[get_temperature_repository] = (
        lambda: DynamoDBTemperatureRepository(dynamodb_resource)
    )
    app.dependency_overrides[get_temperature_data_source] = (
        lambda: mock_temperature_data_source
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_temperature_data_source() -> MockTemperatureDataSource:
    """気象データ取得Portのモックを返す。"""
    return MockTemperatureDataSource()
