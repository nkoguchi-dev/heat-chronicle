import asyncio
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from app.application.temperature.ports.inbound.errors import FetchUnavailable
from app.application.temperature.ports.inbound.fetch_month import (
    FetchMonthStorageUnavailable,
)
from app.application.temperature.ports.outbound.data_source import (
    TemperatureSourceStorageUnavailable,
    TemperatureSourceUnavailable,
)
from app.application.temperature.ports.outbound.fetch_guard import (
    GuardStorageUnavailable,
    GuardSucceeded,
    LeaseLost,
)
from app.infrastructure.repositories.fetch_guard import DynamoDBFetchGuard
from app.infrastructure.scraper.jma_client import (
    JmaClient,
    JmaPageFetched,
    JmaPageStorageUnavailable,
    JmaPageUnavailable,
)
from app.infrastructure.scraper.jma_temperature_data_source import (
    JmaTemperatureDataSource,
)
from tests.fixed_clock import FixedClock
from tests.test_fetch_protection import STATION, make_use_case


@pytest.mark.parametrize(
    "method", ["acquire", "check_owner", "before_attempt", "release"]
)
@pytest.mark.parametrize("expected", [True, False])
async def test_guard_storage_failures_are_distinct_from_contention(
    method: str, expected: bool
) -> None:
    guard = DynamoDBFetchGuard(Mock(), FixedClock())
    guard.table.get_item.return_value = {
        "Item": {
            "station_id": Decimal(0),
            "year_month": "__upstream_lease__",
            "owner_token": guard.token,
            "expires_at": Decimal(str(guard.clock.now().timestamp() + 30)),
        }
    }
    error = ClientError(
        {
            "Error": {
                "Code": "ThrottlingException" if expected else "AccessDeniedException"
            }
        },
        "test",
    )
    if method == "check_owner":
        guard.table.get_item.side_effect = error
    else:
        guard.table.update_item.side_effect = error

    async def call() -> object:
        if method == "before_attempt":
            return await guard.before_attempt()
        return getattr(guard, method)()

    if expected:
        assert isinstance(await call(), GuardStorageUnavailable)
    else:
        with pytest.raises(ClientError) as caught:
            await call()
        assert caught.value is error


@pytest.mark.parametrize(
    "item",
    [
        None,
        {},
        {
            "station_id": Decimal(0),
            "year_month": "__upstream_lease__",
            "expires_at": Decimal(0),
        },
    ],
)
def test_missing_expired_and_malformed_lease(item: Any) -> None:
    guard = DynamoDBFetchGuard(Mock(), FixedClock())
    guard.table.get_item.return_value = {} if item is None else {"Item": item}
    if item == {}:
        with pytest.raises(ValidationError):
            guard.check_owner()
    else:
        assert isinstance(guard.check_owner(), LeaseLost)


@pytest.mark.parametrize("failure", [LeaseLost(), GuardStorageUnavailable()])
async def test_before_attempt_failure_stops_without_http(
    failure: LeaseLost | GuardStorageUnavailable,
) -> None:
    client = JmaClient(AsyncMock(return_value=failure))
    try:
        with patch.object(client._client, "get", new_callable=AsyncMock) as request:
            result = await client.fetch_daily_page(44, "47662", 2024, 1, "s")
        assert isinstance(
            result,
            (
                JmaPageUnavailable
                if isinstance(failure, LeaseLost)
                else JmaPageStorageUnavailable
            ),
        )
        request.assert_not_called()
    finally:
        await client.close()


async def test_lost_lease_during_retry_stops_next_attempt() -> None:
    client = JmaClient(AsyncMock(side_effect=[GuardSucceeded(), LeaseLost()]))
    try:
        with (
            patch.object(
                client._client, "get", side_effect=httpx.ConnectError("private")
            ) as request,
            patch(
                "app.infrastructure.scraper.jma_client.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            assert isinstance(
                await client.fetch_daily_page(44, "47662", 2024, 1, "s"),
                JmaPageUnavailable,
            )
            assert request.call_count == 1
    finally:
        await client.close()


@pytest.mark.parametrize(
    "error",
    [
        httpx.UnsupportedProtocol("private"),
        httpx.InvalidURL("private"),
        ValueError("private"),
    ],
)
async def test_jma_configuration_and_programmer_errors_do_not_retry(
    error: Exception,
) -> None:
    client = JmaClient(AsyncMock(return_value=GuardSucceeded()))
    try:
        with patch.object(client._client, "get", side_effect=error) as request:
            with pytest.raises(type(error)) as caught:
                await client.fetch_daily_page(44, "47662", 2024, 1, "s")
            assert caught.value is error
            assert request.call_count == 1
    finally:
        await client.close()


@pytest.mark.parametrize(
    "page", [JmaPageFetched("html"), JmaPageUnavailable(), JmaPageStorageUnavailable()]
)
async def test_expected_close_failure_keeps_primary_outcome(
    page: JmaPageFetched | JmaPageUnavailable | JmaPageStorageUnavailable,
) -> None:
    client = AsyncMock()
    client.fetch_daily_page.return_value = page
    client.close.side_effect = OSError("private close")
    with patch(
        "app.infrastructure.scraper.jma_temperature_data_source.parse_daily_page",
        return_value=[],
    ):
        result = await JmaTemperatureDataSource(
            lambda: client
        ).fetch_daily_temperatures(STATION, 2024, 1)
    assert isinstance(
        result,
        (
            TemperatureSourceStorageUnavailable
            if isinstance(page, JmaPageStorageUnavailable)
            else TemperatureSourceUnavailable
        ),
    )
    client.close.assert_awaited_once()


@pytest.mark.parametrize("primary", [ValueError("primary"), asyncio.CancelledError()])
async def test_close_failure_preserves_active_exception(primary: BaseException) -> None:
    client = AsyncMock()
    client.fetch_daily_page.side_effect = primary
    client.close.side_effect = RuntimeError("secondary")
    with pytest.raises(type(primary)) as caught:
        await JmaTemperatureDataSource(lambda: client).fetch_daily_temperatures(
            STATION, 2024, 1
        )
    assert caught.value is primary
    client.close.assert_awaited_once()


@pytest.mark.parametrize("page", [JmaPageFetched("html"), JmaPageUnavailable()])
async def test_unexpected_close_failure_reaches_common_error_path(
    page: JmaPageFetched | JmaPageUnavailable,
) -> None:
    client = AsyncMock()
    client.fetch_daily_page.return_value = page
    client.close.side_effect = RuntimeError("secondary")
    with patch(
        "app.infrastructure.scraper.jma_temperature_data_source.parse_daily_page",
        return_value=[],
    ):
        with pytest.raises(RuntimeError, match="secondary"):
            await JmaTemperatureDataSource(lambda: client).fetch_daily_temperatures(
                STATION, 2024, 1
            )


@pytest.mark.parametrize("primary", ["success", "source", "storage"])
async def test_release_storage_failure_preserves_primary_result(primary: str) -> None:
    guard = Mock()
    use_case, _, repo, source = make_use_case(guard)
    guard.release.return_value = GuardStorageUnavailable()
    if primary == "source":
        source.fetch_daily_temperatures.return_value = TemperatureSourceUnavailable()
        with pytest.raises(FetchUnavailable):
            await use_case.fetch_month(1, 2024, 1)
    else:
        if primary == "storage":
            source.fetch_daily_temperatures.return_value = (
                TemperatureSourceStorageUnavailable()
            )
        assert isinstance(
            await use_case.fetch_month(1, 2024, 1), FetchMonthStorageUnavailable
        )
    repo.get_by_station_and_range.assert_not_called()
    guard.release.assert_called_once()


@pytest.mark.parametrize("primary", [ValueError("primary"), asyncio.CancelledError()])
async def test_release_failure_preserves_active_exception(
    primary: BaseException,
) -> None:
    guard = Mock()
    use_case, _, repo, source = make_use_case(guard)
    source.fetch_daily_temperatures.side_effect = primary
    guard.release.side_effect = RuntimeError("secondary")
    with pytest.raises(type(primary)) as caught:
        await use_case.fetch_month(1, 2024, 1)
    assert caught.value is primary
    guard.release.assert_called_once()
    repo.insert_fetch_log.assert_not_called()


async def test_callback_exception_is_not_a_retryable_result() -> None:
    error = ValueError("private callback")
    client = JmaClient(AsyncMock(side_effect=error))
    try:
        with patch.object(client._client, "get", new_callable=AsyncMock) as request:
            with pytest.raises(ValueError) as caught:
                await client.fetch_daily_page(44, "47662", 2024, 1, "s")
            assert caught.value is error
            request.assert_not_called()
    finally:
        await client.close()


async def test_expiry_during_gate_update_prevents_start() -> None:
    clock = FixedClock()
    guard = DynamoDBFetchGuard(Mock(), clock)
    guard.table.get_item.return_value = {
        "Item": {
            "station_id": Decimal(0),
            "year_month": "__upstream_lease__",
            "owner_token": guard.token,
            "expires_at": Decimal(str(clock.now().timestamp() + 30)),
        }
    }
    guard.table.update_item.side_effect = lambda **kwargs: clock.advance(31)
    assert isinstance(await guard.before_attempt(), LeaseLost)


@pytest.mark.parametrize("code", [400, 503])
async def test_http_failure_retries_three_times_without_exposing_details(
    code: int, caplog: pytest.LogCaptureFixture
) -> None:
    client = JmaClient(AsyncMock(return_value=GuardSucceeded()))
    response = httpx.Response(
        code,
        text="private",
        request=httpx.Request("GET", "https://example.com/private"),
    )
    try:
        with (
            patch.object(client._client, "get", return_value=response) as request,
            patch(
                "app.infrastructure.scraper.jma_client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep,
        ):
            assert isinstance(
                await client.fetch_daily_page(44, "47662", 2024, 1, "s"),
                JmaPageUnavailable,
            )
        assert request.call_count == 3
        assert [call.args[0] for call in sleep.await_args_list] == [2, 4]
        assert "private" not in caplog.text
    finally:
        await client.close()
