from dataclasses import dataclass
from datetime import date as Date
from typing import Protocol


@dataclass(frozen=True)
class FetchMonthTemperatureOutput:
    date: Date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


@dataclass(frozen=True)
class FetchMonthStorageUnavailable:
    pass


@dataclass(frozen=True)
class FetchMonthResult:
    records: list[FetchMonthTemperatureOutput]


@dataclass(frozen=True)
class FetchMonthNotFound:
    station_id: int


@dataclass(frozen=True)
class FetchMonthInvalidPeriod:
    detail: str


@dataclass(frozen=True)
class FetchMonthUnavailable:
    pass


class FetchMonthPort(Protocol):
    async def fetch_month(
        self, station_id: int, year: int, month: int
    ) -> (
        FetchMonthResult
        | FetchMonthNotFound
        | FetchMonthInvalidPeriod
        | FetchMonthStorageUnavailable
        | FetchMonthUnavailable
    ): ...
