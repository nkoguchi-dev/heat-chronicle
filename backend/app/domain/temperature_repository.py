from datetime import datetime
from typing import Protocol

from app.domain.temperature import DailyTemperature


class TemperatureRepository(Protocol):
    def get_by_station_and_range(
        self, station_id: int, start_date: str, end_date: str
    ) -> list[DailyTemperature]: ...

    def get_fetched_months(
        self, station_id: int
    ) -> dict[tuple[int, int], datetime]: ...

    def bulk_insert_temperatures(
        self, station_id: int, records: list[DailyTemperature]
    ) -> None: ...

    def insert_fetch_log(self, station_id: int, year: int, month: int) -> None: ...
