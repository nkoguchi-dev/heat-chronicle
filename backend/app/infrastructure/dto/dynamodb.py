from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

DateString = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
YearMonthString = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}$")]


class StationItemDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: Decimal
    station_name: str
    prec_no: Decimal
    block_no: str
    station_type: Literal["s", "a"]
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    earliest_year: Decimal | None = None


class DailyTemperatureItemDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    station_id: Decimal
    date: DateString
    max_temp: Decimal | None = None
    min_temp: Decimal | None = None
    avg_temp: Decimal | None = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class DailyTemperatureWriteDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    station_id: int
    date: DateString
    max_temp: Decimal | None = None
    min_temp: Decimal | None = None
    avg_temp: Decimal | None = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class FetchLogItemDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    station_id: Decimal
    year_month: YearMonthString
    fetched_at: str

    @field_validator("year_month")
    @classmethod
    def validate_year_month(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m")
        return value

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("fetched_at must include timezone information")
        return value


class FetchLogWriteDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    station_id: int
    year_month: YearMonthString
    fetched_at: str

    @field_validator("year_month")
    @classmethod
    def validate_year_month(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m")
        return value

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("fetched_at must include timezone information")
        return value


class StationSeedDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: int = Field(gt=0)
    station_name: str
    prec_no: int
    block_no: str
    station_type: Literal["s", "a"]
    latitude: float | None = None
    longitude: float | None = None
    earliest_year: int | None = None


class StationWriteDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: int = Field(gt=0)
    station_name: str
    prec_no: int
    block_no: str
    station_type: Literal["s", "a"]
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    earliest_year: int | None = None


class StationMetadataItemDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: Decimal
    schema_version: Decimal


class StationMetadataWriteDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: Literal[0]
    schema_version: int = Field(ge=0)
