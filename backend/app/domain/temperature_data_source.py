from typing import Protocol

from app.domain.station import Station
from app.domain.temperature import DailyTemperature


class TemperatureDataSource(Protocol):
    async def fetch_daily_temperatures(
        self,
        station: Station,
        year: int,
        month: int,
    ) -> list[DailyTemperature]: ...
