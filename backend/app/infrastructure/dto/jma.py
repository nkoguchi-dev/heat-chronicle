from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JmaDailyPageRequestDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    prec_no: int
    block_no: str
    year: int
    month: int = Field(ge=1, le=12)
    station_type: Literal["s", "a"]

    @property
    def page(self) -> str:
        return "daily_s1.php" if self.station_type == "s" else "daily_a1.php"

    def to_query_params(self) -> dict[str, str | int]:
        return {
            "prec_no": self.prec_no,
            "block_no": self.block_no,
            "year": self.year,
            "month": self.month,
            "day": "",
            "view": "p1",
        }


class JmaDailyTemperatureDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    date: Date
    max_temp: float | None
    min_temp: float | None
    avg_temp: float | None
