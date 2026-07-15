from app.domain.station import Station
from app.domain.temperature import DailyTemperature
from app.infrastructure.scraper.jma_client import JmaClient
from app.infrastructure.scraper.jma_parser import parse_daily_page


class JmaTemperatureDataSource:
    async def fetch_daily_temperatures(
        self,
        station: Station,
        year: int,
        month: int,
    ) -> list[DailyTemperature]:
        client = JmaClient()
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
