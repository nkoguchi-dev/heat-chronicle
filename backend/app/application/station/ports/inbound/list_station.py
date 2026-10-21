from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class StationOutput:
    id: int
    station_name: str
    prec_no: int
    block_no: str
    station_type: Literal["s", "a"]
    latitude: float | None = None
    longitude: float | None = None
    earliest_year: int | None = None


@dataclass(frozen=True)
class ListStationStorageUnavailable:
    pass


@dataclass(frozen=True)
class StationListResult:
    stations: list[StationOutput]


@dataclass(frozen=True)
class ListStationNotFound:
    pass


class ListStationPort(Protocol):
    def list_stations(
        self, prec_no: int | None = None
    ) -> StationListResult | ListStationNotFound | ListStationStorageUnavailable:
        """Return a successful catalog, missing region, or storage failure."""
        ...
