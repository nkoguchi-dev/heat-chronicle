from dataclasses import dataclass
from typing import Protocol

from app.domain.station.model import Station


@dataclass(frozen=True)
class StationsRead:
    stations: list[Station]


@dataclass(frozen=True)
class StationFound:
    station: Station


@dataclass(frozen=True)
class StationMissing:
    pass


@dataclass(frozen=True)
class StationStorageUnavailable:
    pass


class StationRepository(Protocol):
    def get_all(self) -> StationsRead | StationStorageUnavailable: ...

    def get_by_prec_no(
        self, prec_no: int
    ) -> StationsRead | StationStorageUnavailable: ...

    def get_by_id(
        self, station_id: int
    ) -> StationFound | StationMissing | StationStorageUnavailable: ...
