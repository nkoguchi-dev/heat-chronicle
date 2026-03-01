from datetime import date

from pydantic import BaseModel


class StationResponse(BaseModel):
    id: int
    station_name: str
    prec_no: int
    block_no: str
    station_type: str
    latitude: float | None = None
    longitude: float | None = None
    earliest_year: int | None = None


class PrefectureResponse(BaseModel):
    prec_no: int
    name: str


class TemperatureRecord(BaseModel):
    date: date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


class TemperatureMetadata(BaseModel):
    station_id: int
    station_name: str
    start_year: int
    end_year: int
    total_records: int
    fetched_months: list[str]
    fetching_required: bool
    has_older_data: bool
    next_end_year: int | None


class TemperatureResponse(BaseModel):
    metadata: TemperatureMetadata
    data: list[TemperatureRecord]


class MonthTemperatureResponse(BaseModel):
    year: int
    month: int
    records: list[TemperatureRecord]
