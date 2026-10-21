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


class FetchMonthPort(Protocol):
    async def fetch_month(
        self, station_id: int, year: int, month: int
    ) -> list[FetchMonthTemperatureOutput] | FetchMonthStorageUnavailable: ...
