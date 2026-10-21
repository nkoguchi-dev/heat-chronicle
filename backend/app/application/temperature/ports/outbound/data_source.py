from dataclasses import dataclass
from typing import Protocol

from app.domain.station.model import Station
from app.domain.temperature.model import DailyTemperature


@dataclass(frozen=True)
class TemperaturesFetched:
    records: list[DailyTemperature]


@dataclass(frozen=True)
class TemperatureSourceUnavailable:
    pass


@dataclass(frozen=True)
class TemperatureSourceStorageUnavailable:
    pass


class TemperatureDataSource(Protocol):
    async def fetch_daily_temperatures(
        self,
        station: Station,
        year: int,
        month: int,
    ) -> (
        TemperaturesFetched
        | TemperatureSourceUnavailable
        | TemperatureSourceStorageUnavailable
    ): ...
