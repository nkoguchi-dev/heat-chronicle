from collections.abc import Callable

from app.domain.station.model import Station
from app.domain.temperature.model import DailyTemperature
from app.infrastructure.scraper.jma_client import JmaClient
from app.infrastructure.scraper.jma_parser import parse_daily_page


class JmaTemperatureDataSource:
    def __init__(self, client_factory: Callable[[], JmaClient]) -> None:
        self.client_factory = client_factory

    async def fetch_daily_temperatures(
        self,
        station: Station,
        year: int,
        month: int,
    ) -> list[DailyTemperature]:
        client = self.client_factory()
        try:
            html = await client.fetch_daily_page(
                prec_no=station.prec_no,
                block_no=station.block_no,
                year=year,
                month=month,
                station_type=station.station_type,
            )
            return parse_daily_page(
                html,
                year,
                month,
                station.station_type,
            )
        finally:
            await client.close()
