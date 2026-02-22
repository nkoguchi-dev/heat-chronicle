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


class TemperatureResponse(BaseModel):
    metadata: TemperatureMetadata
    data: list[TemperatureRecord]
