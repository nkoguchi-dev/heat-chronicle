from dataclasses import dataclass
from typing import Literal

from app.domain.station.repository import StationRepository


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


class GetStationUseCase:
    def __init__(self, station_repo: StationRepository):
        self.station_repo = station_repo

    def get_stations(self, prec_no: int | None = None) -> list[StationOutput]:
        if prec_no is not None:
            stations = self.station_repo.get_by_prec_no(prec_no)
        else:
            stations = self.station_repo.get_all()

        return [
            StationOutput(
                id=station.id,
                station_name=station.station_name,
                prec_no=station.prec_no,
                block_no=station.block_no,
                station_type=station.station_type,
                latitude=station.latitude,
                longitude=station.longitude,
                earliest_year=station.earliest_year,
            )
            for station in stations
        ]
