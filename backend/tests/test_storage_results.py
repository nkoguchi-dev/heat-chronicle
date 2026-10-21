from datetime import date
from typing import Any
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.application.station.ports.inbound.list_station import (
    ListStationStorageUnavailable,
)
from app.application.station.ports.outbound.repository import StationStorageUnavailable
from app.application.temperature.ports.inbound.fetch_month import (
    FetchMonthStorageUnavailable,
)
from app.application.temperature.ports.inbound.get_temperature import (
    GetTemperatureStorageUnavailable,
)
from app.application.temperature.ports.outbound.repository import (
    FetchedMonthsRead,
    TemperatureStorageUnavailable,
)
from app.domain.temperature.model import DailyTemperature
from app.infrastructure.repositories.station_repository import DynamoDBStationRepository
from app.infrastructure.repositories.storage_errors import expected_storage_failure
from app.infrastructure.repositories.temperature_repository import (
    DynamoDBTemperatureRepository,
)
from app.presentation.api.shared.dependencies import (
    get_fetch_month_port,
    get_station_port,
    get_temperature_port,
)
from app.presentation.api.stations.get_stations import router as station_router
from app.presentation.api.temperature import router as temperature_router
from tests.fixed_clock import FixedClock
from tests.test_fetch_protection import make_use_case

OPERATIONS: list[tuple[str, str, tuple[object, ...]]] = [
    ("station", "get_all", ()),
    ("station", "get_by_prec_no", (44,)),
    ("station", "get_by_id", (4,)),
    ("temperature", "get_by_station_and_range", (4, "2024-01-01", "2024-12-31")),
    ("temperature", "get_fetched_months", (4,)),
    ("temperature", "bulk_insert_temperatures", (4, [])),
    ("temperature", "insert_fetch_log", (4, 2024, 1)),
]


@pytest.mark.parametrize("kind,method,args", OPERATIONS)
@pytest.mark.parametrize("expected", [True, False])
def test_repository_catches_only_expected_io_failures(
    kind: str, method: str, args: tuple[object, ...], expected: bool
) -> None:
    repo: Any = (
        DynamoDBStationRepository(Mock())
        if kind == "station"
        else DynamoDBTemperatureRepository(Mock(), FixedClock())
    )
    code = (
        "ProvisionedThroughputExceededException"
        if expected
        else "AccessDeniedException"
    )
    error = ClientError({"Error": {"Code": code, "Message": "private"}}, method)
    with patch.object(repo, "_" + method, side_effect=error):
        if expected:
            result = getattr(repo, method)(*args)
            assert isinstance(
                result, (StationStorageUnavailable, TemperatureStorageUnavailable)
            )
        else:
            with pytest.raises(ClientError) as caught:
                getattr(repo, method)(*args)
            assert caught.value is error


@pytest.mark.parametrize(
    "code",
    [
        "ThrottlingException",
        "RequestLimitExceeded",
        "InternalServerError",
        "ServiceUnavailable",
    ],
)
def test_storage_error_code_classification(code: str) -> None:
    assert expected_storage_failure(
        ClientError({"Error": {"Code": code}}, "read"), "read"
    )


def test_network_failure_is_a_value_but_dto_bug_is_not() -> None:
    repo = DynamoDBStationRepository(Mock())
    with patch.object(
        repo,
        "_get_all",
        side_effect=EndpointConnectionError(endpoint_url="http://local"),
    ):
        assert isinstance(repo.get_all(), StationStorageUnavailable)
    with patch.object(repo, "_get_all", side_effect=ValueError("corrupt DTO")):
        with pytest.raises(ValueError, match="corrupt DTO"):
            repo.get_all()


@pytest.mark.parametrize("phase", ["initial", "reread", "bulk"])
async def test_month_storage_failure_stops_following_writes_and_releases(
    phase: str,
) -> None:
    guard = Mock()
    use_case, _, repo, source = make_use_case(guard)
    if phase == "initial":
        repo.get_fetched_months.return_value = TemperatureStorageUnavailable()
    elif phase == "reread":
        repo.get_fetched_months.side_effect = [
            FetchedMonthsRead({}),
            TemperatureStorageUnavailable(),
        ]
    else:
        source.fetch_daily_temperatures.return_value = [
            DailyTemperature(date(2024, 1, 1))
        ]
        repo.bulk_insert_temperatures.return_value = TemperatureStorageUnavailable()
    assert isinstance(
        await use_case.fetch_month(1, 2024, 1), FetchMonthStorageUnavailable
    )
    repo.insert_fetch_log.assert_not_called()
    if phase == "initial":
        guard.acquire.assert_not_called()
        guard.release.assert_not_called()
    else:
        guard.release.assert_called_once()


@pytest.mark.parametrize("route", ["station", "temperature", "month"])
async def test_storage_result_keeps_generic_500_at_http_boundary(route: str) -> None:
    app = FastAPI()
    app.include_router(station_router, prefix="/api/stations")
    app.include_router(temperature_router, prefix="/api/temperature")
    fake = Mock()
    fake.list_stations.return_value = ListStationStorageUnavailable()
    fake.get_temperature_data.return_value = GetTemperatureStorageUnavailable()
    from unittest.mock import AsyncMock

    fake.fetch_month = AsyncMock(return_value=FetchMonthStorageUnavailable())
    app.dependency_overrides[get_station_port] = lambda: fake
    app.dependency_overrides[get_temperature_port] = lambda: fake
    app.dependency_overrides[get_fetch_month_port] = lambda: fake
    paths = {
        "station": "/api/stations/",
        "temperature": "/api/temperature/4",
        "month": "/api/temperature/4/fetch-month?year=2024&month=1",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(paths[route])
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Retry-After" not in response.headers


def test_use_cases_map_station_storage_failure_to_their_own_result() -> None:
    from app.application.station.list_station_use_case import ListStationUseCase
    from app.application.temperature.get_temperature_use_case import (
        GetTemperatureUseCase,
    )

    station_repo = Mock()
    station_repo.get_all.return_value = StationStorageUnavailable()
    station_repo.get_by_id.return_value = StationStorageUnavailable()
    assert isinstance(
        ListStationUseCase(station_repo).list_stations(), ListStationStorageUnavailable
    )
    assert isinstance(
        GetTemperatureUseCase(station_repo, Mock(), FixedClock()).get_temperature_data(
            4, 2024
        ),
        GetTemperatureStorageUnavailable,
    )


async def test_fetch_log_write_failure_does_not_read_success_and_releases() -> None:
    guard = Mock()
    use_case, _, repo, _ = make_use_case(guard)
    repo.insert_fetch_log.return_value = TemperatureStorageUnavailable()
    assert isinstance(
        await use_case.fetch_month(1, 2024, 1), FetchMonthStorageUnavailable
    )
    repo.get_by_station_and_range.assert_not_called()
    guard.release.assert_called_once()
