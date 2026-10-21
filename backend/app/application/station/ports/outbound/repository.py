from typing import Protocol

from app.domain.station.model import Station


class StationRepository(Protocol):
    def get_all(self) -> list[Station]: ...

    def get_by_prec_no(self, prec_no: int) -> list[Station]: ...

    def get_by_id(self, station_id: int) -> Station | None: ...
