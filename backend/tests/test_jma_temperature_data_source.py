from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.application.temperature.ports.outbound.data_source import TemperaturesFetched
from app.domain.station.model import Station
from app.domain.temperature.model import DailyTemperature
from app.infrastructure.scraper.jma_client import JmaPageFetched
from app.infrastructure.scraper.jma_temperature_data_source import (
    JmaTemperatureDataSource,
)


@pytest.mark.asyncio
async def test_fetch_daily_temperatures() -> None:
    station = Station(
        id=47662,
        station_name="東京",
        prec_no=44,
        block_no="47662",
        station_type="s",
    )
    expected = [
        DailyTemperature(
            date=date(2024, 8, 1),
            max_temp=35.0,
            min_temp=25.0,
            avg_temp=30.0,
        )
    ]
    client = AsyncMock()
    client.fetch_daily_page.return_value = JmaPageFetched("<html></html>")

    with (
        patch(
            "app.infrastructure.scraper.jma_temperature_data_source.parse_daily_page",
            return_value=expected,
        ) as parser,
    ):
        result = await JmaTemperatureDataSource(
            lambda: client
        ).fetch_daily_temperatures(
            station,
            2024,
            8,
        )

    assert result == TemperaturesFetched(expected)
    client.fetch_daily_page.assert_awaited_once_with(
        prec_no=44,
        block_no="47662",
        year=2024,
        month=8,
        station_type="s",
    )
    parser.assert_called_once_with("<html></html>", 2024, 8, "s")
    client.close.assert_awaited_once_with()


@pytest.mark.parametrize("failure", ["fetch", "parse"])
async def test_client_is_closed_on_failure(failure: str) -> None:
    client = AsyncMock()
    client.fetch_daily_page.return_value = JmaPageFetched("html")
    if failure == "fetch":
        client.fetch_daily_page.side_effect = RuntimeError("failed fetch")
    with patch(
        "app.infrastructure.scraper.jma_temperature_data_source.parse_daily_page",
        side_effect=ValueError("failed parse"),
    ):
        with pytest.raises((RuntimeError, ValueError)):
            await JmaTemperatureDataSource(lambda: client).fetch_daily_temperatures(
                Station(4, "東京", 44, "47662", "s"), 2024, 8
            )
    client.close.assert_awaited_once_with()


async def test_client_is_created_per_fetch_and_closed_on_cancellation() -> None:
    import asyncio

    client = AsyncMock()
    client.fetch_daily_page.side_effect = asyncio.CancelledError()
    factory = Mock(return_value=client)
    source = JmaTemperatureDataSource(factory)
    factory.assert_not_called()
    with pytest.raises(asyncio.CancelledError):
        await source.fetch_daily_temperatures(
            Station(4, "東京", 44, "47662", "s"), 2024, 8
        )
    factory.assert_called_once_with()
    client.close.assert_awaited_once_with()
