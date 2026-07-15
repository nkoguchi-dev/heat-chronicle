from dataclasses import dataclass
from typing import Literal

StationType = Literal["s", "a"]


@dataclass(frozen=True)
class Station:
    id: int
    station_name: str
    prec_no: int
    block_no: str
    station_type: StationType
    latitude: float | None = None
    longitude: float | None = None
    earliest_year: int | None = None
