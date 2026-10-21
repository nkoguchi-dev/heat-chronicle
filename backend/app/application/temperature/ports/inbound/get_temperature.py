from dataclasses import dataclass
from datetime import date as Date
from typing import Protocol


@dataclass(frozen=True)
class TemperatureMetadataOutput:
    station_id: int
    station_name: str
    start_year: int
    end_year: int
    total_records: int
    fetched_months: list[str]
    fetching_required: bool
    has_older_data: bool
    next_end_year: int | None


@dataclass(frozen=True)
class TemperatureRecordOutput:
    date: Date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


@dataclass(frozen=True)
class GetTemperatureDataOutput:
    metadata: TemperatureMetadataOutput
    data: list[TemperatureRecordOutput]


class GetTemperaturePort(Protocol):
    def get_temperature_data(
        self, station_id: int, end_year: int | None
    ) -> GetTemperatureDataOutput: ...
