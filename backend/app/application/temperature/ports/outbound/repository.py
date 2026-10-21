from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.temperature.model import DailyTemperature


@dataclass(frozen=True)
class TemperaturesRead:
    records: list[DailyTemperature]


@dataclass(frozen=True)
class FetchedMonthsRead:
    months: dict[tuple[int, int], datetime]


@dataclass(frozen=True)
class TemperatureWriteSucceeded:
    pass


@dataclass(frozen=True)
class TemperatureStorageUnavailable:
    pass


class TemperatureRepository(Protocol):
    def get_by_station_and_range(
        self, station_id: int, start_date: str, end_date: str
    ) -> TemperaturesRead | TemperatureStorageUnavailable: ...

    def get_fetched_months(
        self, station_id: int
    ) -> FetchedMonthsRead | TemperatureStorageUnavailable: ...

    def bulk_insert_temperatures(
        self, station_id: int, records: list[DailyTemperature]
    ) -> TemperatureWriteSucceeded | TemperatureStorageUnavailable: ...

    def insert_fetch_log(
        self, station_id: int, year: int, month: int
    ) -> TemperatureWriteSucceeded | TemperatureStorageUnavailable: ...
