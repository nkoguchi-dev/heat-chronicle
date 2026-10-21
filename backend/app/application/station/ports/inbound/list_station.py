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


class PrefectureNotFound(ValueError):
    """The requested region has no stations; preserve the public 404 message."""


@dataclass(frozen=True)
class ListStationStorageUnavailable:
    pass


class ListStationPort(Protocol):
    def list_stations(
        self, prec_no: int | None = None
    ) -> list[StationOutput] | ListStationStorageUnavailable:
        """Return station outputs; raise PrefectureNotFound for an empty region."""
        ...
