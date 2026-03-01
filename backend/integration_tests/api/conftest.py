from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.di.container import get_station_repository, get_temperature_repository
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import TemperatureRepository
from app.main import app
from integration_tests.fixtures.mock_overrides import MockJmaClient


@asynccontextmanager
async def _noop_lifespan(application: Any) -> AsyncGenerator[None, None]:
    """lifespan を無効化する（ensure_tables_exist / seed_and_migrate をスキップ）。"""
    yield


@pytest.fixture
async def client(
    dynamodb_resource: Any, test_settings: Settings
) -> AsyncGenerator[AsyncClient, None]:
    """テストごとに新しい AsyncClient を作成する。
    DI をオーバーライドしてテスト用 DynamoDB を注入し、lifespan を無効化する。
    """
    app.router.lifespan_context = _noop_lifespan

    app.dependency_overrides[get_station_repository] = lambda: StationRepository(
        dynamodb_resource
    )
    app.dependency_overrides[get_temperature_repository] = (
        lambda: TemperatureRepository(dynamodb_resource)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_jma_client() -> MockJmaClient:
    """JmaClient のモックインスタンスを返す。"""
    return MockJmaClient()


@pytest.fixture(autouse=True)
def patch_jma_client(mock_jma_client: MockJmaClient) -> Any:
    """ScrapeService 内の JmaClient をモックに差し替える。
    autouse により、全テストで JmaClient が差し替えられる。
    未設定リクエストは RuntimeError で即座に検知できる。
    """
    with patch(
        "app.application.scrape_service.JmaClient",
        return_value=mock_jma_client,
    ):
        yield
