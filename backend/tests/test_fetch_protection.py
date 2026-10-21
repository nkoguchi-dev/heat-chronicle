import asyncio
from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import AsyncMock, Mock, patch

import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws

from app.application.shared.ports.outbound.clock import Clock
from app.application.temperature.fetch_month_use_case import FetchMonthUseCase
from app.application.temperature.get_temperature_use_case import GetTemperatureUseCase
from app.application.temperature.ports.inbound.errors import (
    InvalidTemperatureInput as GetTemperatureInputError,
)
from app.config import Settings
from app.di.container import get_fetch_month_use_case
from app.domain.station.model import Station
from app.domain.temperature.fetch_guard import FetchUnavailable
from app.domain.temperature.input_policy import InvalidTemperatureInput, validate_month
from app.infrastructure.repositories.fetch_guard import DynamoDBFetchGuard
from app.main import app
from tests.fixed_clock import FixedClock

STATION = Station(1, "Tokyo", 44, "47662", "s", earliest_year=1872)
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def dynamodb() -> Generator[Any, None, None]:
    with (
        mock_aws(),
        patch(
            "app.infrastructure.repositories.fetch_guard.settings",
            Settings(dynamodb_table_prefix=""),
        ),
    ):
        db = boto3.resource("dynamodb", region_name="ap-northeast-1")
        db.create_table(
            TableName="fetch-log",
            KeySchema=[
                {"AttributeName": "station_id", "KeyType": "HASH"},
                {"AttributeName": "year_month", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "station_id", "AttributeType": "N"},
                {"AttributeName": "year_month", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield db


def test_shared_lease_expiry_and_stale_owner(dynamodb: Any) -> None:
    clock = FixedClock(datetime.fromtimestamp(100, timezone.utc))
    a, b = DynamoDBFetchGuard(dynamodb, clock), DynamoDBFetchGuard(dynamodb, clock)
    a.acquire()
    with pytest.raises(FetchUnavailable):
        b.acquire()
    clock.advance(31)
    b.acquire()
    a.release()
    b.check_owner()
    with pytest.raises(FetchUnavailable):
        a.check_owner()
    b.release()
    a.acquire()


async def test_interval_survives_owner_handoff(dynamodb: Any) -> None:
    clock = FixedClock(datetime.fromtimestamp(100, timezone.utc))
    a, b = DynamoDBFetchGuard(dynamodb, clock), DynamoDBFetchGuard(dynamodb, clock)

    async def sleep(seconds: float) -> None:
        clock.advance(seconds)

    with patch(
        "app.infrastructure.repositories.fetch_guard.asyncio.sleep", side_effect=sleep
    ):
        a.acquire()
        await a.before_attempt()
        a.release()
        b.acquire()
        await b.before_attempt()
        assert clock.now().timestamp() == 102
        await b.before_attempt()
        assert clock.now().timestamp() == 104


def make_use_case(
    guard: Any = None, clock: Clock | None = None
) -> tuple[FetchMonthUseCase, Mock, Mock, AsyncMock]:
    station_repo, repo, source = Mock(), Mock(), AsyncMock()
    station_repo.get_by_id.return_value = STATION
    repo.get_fetched_months.return_value = {}
    repo.get_by_station_and_range.return_value = []
    source.fetch_daily_temperatures.return_value = []
    return (
        FetchMonthUseCase(
            station_repo, repo, source, guard or Mock(), clock or FixedClock()
        ),
        station_repo,
        repo,
        source,
    )


@pytest.mark.parametrize(
    "year,month", [(1871, 12), (2027, 1), (2026, 2), (2026, 0), (2026, 13)]
)
async def test_reject_before_temperature_io(year: int, month: int) -> None:
    use_case, _, repo, source = make_use_case()
    with pytest.raises(InvalidTemperatureInput):
        await use_case.fetch_month(1, year, month)
    repo.get_fetched_months.assert_not_called()
    repo.bulk_insert_temperatures.assert_not_called()
    repo.insert_fetch_log.assert_not_called()
    source.fetch_daily_temperatures.assert_not_called()


async def test_unknown_station_precedes_month_validation() -> None:
    use_case, stations, repo, source = make_use_case()
    stations.get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        await use_case.fetch_month(2, 0, 0)
    repo.get_fetched_months.assert_not_called()
    source.fetch_daily_temperatures.assert_not_called()


@pytest.mark.parametrize("year,month", [(1872, 1), (2026, 1)])
def test_observation_boundaries(year: int, month: int) -> None:
    validate_month(STATION, year, month, NOW)


async def test_empty_success_is_cached_and_failure_is_not() -> None:
    use_case, _, repo, source = make_use_case()
    await use_case.fetch_month(1, 2024, 1)
    repo.insert_fetch_log.assert_called_once_with(1, 2024, 1)
    repo.bulk_insert_temperatures.assert_not_called()
    repo.reset_mock()
    source.fetch_daily_temperatures.side_effect = RuntimeError(
        "private upstream detail"
    )
    with pytest.raises(FetchUnavailable):
        await use_case.fetch_month(1, 2024, 1)
    repo.insert_fetch_log.assert_not_called()


async def test_recheck_cache_after_acquiring_lease() -> None:
    guard = Mock()
    use_case, _, repo, source = make_use_case(guard)
    repo.get_fetched_months.side_effect = [{}, {(2024, 1): NOW}]
    await use_case.fetch_month(1, 2024, 1)
    source.fetch_daily_temperatures.assert_not_called()
    guard.release.assert_called_once()


async def test_lost_owner_cannot_write() -> None:
    guard = Mock()
    guard.check_owner.side_effect = FetchUnavailable()
    use_case, _, repo, _ = make_use_case(guard)
    with pytest.raises(FetchUnavailable):
        await use_case.fetch_month(1, 2024, 1)
    repo.bulk_insert_temperatures.assert_not_called()
    repo.insert_fetch_log.assert_not_called()
    guard.release.assert_called_once()


@pytest.mark.parametrize("station_id", [1, 2])
async def test_other_execution_rejected_for_same_or_different_station(
    dynamodb: Any, station_id: int
) -> None:
    first, second = DynamoDBFetchGuard(dynamodb, FixedClock()), DynamoDBFetchGuard(
        dynamodb, FixedClock()
    )
    use_case, _, repo, source = make_use_case(second)
    first.acquire()
    with pytest.raises(FetchUnavailable):
        await use_case.fetch_month(station_id, 2024, 1)
    source.fetch_daily_temperatures.assert_not_called()
    repo.insert_fetch_log.assert_not_called()


@pytest.mark.parametrize("end_year", [0, 1871, 10000])
def test_history_rejects_before_temperature_io(end_year: int) -> None:
    stations, repo = Mock(), Mock()
    stations.get_by_id.return_value = STATION
    with pytest.raises(GetTemperatureInputError):
        GetTemperatureUseCase(stations, repo, FixedClock()).get_temperature_data(
            1, end_year
        )
    repo.get_by_station_and_range.assert_not_called()
    repo.get_fetched_months.assert_not_called()


@pytest.mark.parametrize("station_id,status", [(0, 422), (-1, 422), (999, 404)])
async def test_http_invalid_station_has_no_upstream(
    station_id: int, status: int
) -> None:
    use_case, stations, repo, source = make_use_case()
    stations.get_by_id.return_value = None
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_fetch_month_use_case] = lambda: use_case
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/api/temperature/{station_id}/fetch-month?year=0&month=0"
            )
        assert response.status_code == status
        source.fetch_daily_temperatures.assert_not_called()
        repo.insert_fetch_log.assert_not_called()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


async def test_http_busy_is_safe_retryable_response() -> None:
    use_case = Mock()
    use_case.fetch_month = AsyncMock(side_effect=FetchUnavailable("private detail"))
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_fetch_month_use_case] = lambda: use_case
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/temperature/1/fetch-month?year=2024&month=1",
                headers={"Origin": "http://localhost:3000"},
            )
        assert response.status_code == 503
        assert response.json() == {"detail": "Temporarily unavailable"}
        assert response.headers["Retry-After"] == "5"
        assert "Retry-After" in response.headers["Access-Control-Expose-Headers"]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


async def test_budget_timeout_releases_lease_without_success_log() -> None:
    guard = Mock()
    use_case, _, repo, source = make_use_case(guard)
    source.fetch_daily_temperatures.side_effect = lambda *args: None

    async def slow(*args: object) -> list[Any]:
        await asyncio.sleep(0.05)
        return []

    source.fetch_daily_temperatures.side_effect = slow
    with patch(
        "app.application.temperature.fetch_month_use_case.FETCH_BUDGET_SECONDS", 0.01
    ):
        with pytest.raises(FetchUnavailable):
            await use_case.fetch_month(1, 2024, 1)
    repo.insert_fetch_log.assert_not_called()
    guard.release.assert_called_once()


async def test_two_overlapping_requests_share_one_upstream(dynamodb: Any) -> None:
    first, _, _, source = make_use_case(DynamoDBFetchGuard(dynamodb, FixedClock()))
    second, _, repo, other_source = make_use_case(
        DynamoDBFetchGuard(dynamodb, FixedClock())
    )
    started, finish = asyncio.Event(), asyncio.Event()

    async def fetch(*args: object) -> list[Any]:
        started.set()
        await finish.wait()
        return []

    source.fetch_daily_temperatures.side_effect = fetch
    task = asyncio.create_task(first.fetch_month(1, 2024, 1))
    await started.wait()
    try:
        with pytest.raises(FetchUnavailable):
            await second.fetch_month(1, 2024, 1)
        other_source.fetch_daily_temperatures.assert_not_called()
        repo.insert_fetch_log.assert_not_called()
    finally:
        finish.set()
        await task


@pytest.mark.parametrize("elapsed,expect_failure", [(0, False), (26, True)])
async def test_budget_uses_elapsed_clock_not_wall_time(
    elapsed: float, expect_failure: bool
) -> None:
    clock = FixedClock()
    use_case, _, repo, source = make_use_case(clock=clock)

    async def fetch(*args: object) -> list[Any]:
        # Simulate an NTP/wall-clock adjustment independently of elapsed time.
        clock.wall_time = datetime(2030, 1, 1, tzinfo=timezone.utc)
        clock.elapsed_seconds += elapsed
        return []

    source.fetch_daily_temperatures.side_effect = fetch
    if expect_failure:
        with pytest.raises(FetchUnavailable):
            await use_case.fetch_month(1, 2024, 1)
        repo.insert_fetch_log.assert_not_called()
    else:
        await use_case.fetch_month(1, 2024, 1)
        repo.insert_fetch_log.assert_called_once()


@pytest.mark.parametrize(
    "instant,year",
    [
        ("2025-12-31T14:59:59+00:00", 2025),
        ("2025-12-31T15:00:00+00:00", 2026),
    ],
)
def test_history_uses_japan_year_from_injected_clock(instant: str, year: int) -> None:
    clock = FixedClock(datetime.fromisoformat(instant))
    stations, repo = Mock(), Mock()
    stations.get_by_id.return_value = STATION
    repo.get_fetched_months.return_value = {}
    repo.get_by_station_and_range.return_value = []
    result = GetTemperatureUseCase(stations, repo, clock).get_temperature_data(1, None)
    assert result.metadata.end_year == year
    assert result.metadata.start_year == year - 49
