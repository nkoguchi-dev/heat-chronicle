import logging
import sys
from collections.abc import Callable
from typing import assert_never

import httpx

from app.application.temperature.ports.outbound.data_source import (
    TemperaturesFetched,
    TemperatureSourceStorageUnavailable,
    TemperatureSourceUnavailable,
)
from app.domain.station.model import Station
from app.infrastructure.scraper.jma_client import (
    JmaClient,
    JmaPageFetched,
    JmaPageStorageUnavailable,
    JmaPageUnavailable,
)
from app.infrastructure.scraper.jma_parser import parse_daily_page

logger = logging.getLogger(__name__)


class JmaTemperatureDataSource:
    def __init__(self, client_factory: Callable[[], JmaClient]) -> None:
        self.client_factory = client_factory

    async def fetch_daily_temperatures(
        self, station: Station, year: int, month: int
    ) -> (
        TemperaturesFetched
        | TemperatureSourceUnavailable
        | TemperatureSourceStorageUnavailable
    ):
        client = self.client_factory()
        result: (
            TemperaturesFetched
            | TemperatureSourceUnavailable
            | TemperatureSourceStorageUnavailable
        ) = TemperatureSourceUnavailable()
        try:
            match await client.fetch_daily_page(
                prec_no=station.prec_no,
                block_no=station.block_no,
                year=year,
                month=month,
                station_type=station.station_type,
            ):
                case JmaPageFetched(html=html):
                    result = TemperaturesFetched(
                        parse_daily_page(html, year, month, station.station_type)
                    )
                case JmaPageUnavailable():
                    result = TemperatureSourceUnavailable()
                case JmaPageStorageUnavailable():
                    result = TemperatureSourceStorageUnavailable()
                case unreachable:
                    assert_never(unreachable)
        finally:
            active_error = sys.exception()
            try:
                await client.close()
            except httpx.RequestError, OSError, TimeoutError:
                logger.warning("jma_close_unavailable")
                if active_error is None and isinstance(result, TemperaturesFetched):
                    result = TemperatureSourceUnavailable()
            except BaseException:
                # Cleanup must not mask an active cancellation or unexpected failure.
                if active_error is None:
                    raise
                logger.warning("jma_close_failed_during_exception")
        return result
