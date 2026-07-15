from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.station import Station
from app.domain.temperature import DailyTemperature
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
    client.fetch_daily_page.return_value = "<html></html>"

    with (
        patch(
            "app.infrastructure.scraper.jma_temperature_data_source.JmaClient",
            return_value=client,
        ),
        patch(
            "app.infrastructure.scraper.jma_temperature_data_source.parse_daily_page",
            return_value=expected,
        ) as parser,
    ):
        result = await JmaTemperatureDataSource().fetch_daily_temperatures(
            station,
            2024,
            8,
        )

    assert result == expected
    client.fetch_daily_page.assert_awaited_once_with(
        prec_no=44,
        block_no="47662",
        year=2024,
        month=8,
        station_type="s",
    )
    parser.assert_called_once_with("<html></html>", 2024, 8, "s")
    client.close.assert_awaited_once_with()
