from app.application.station.ports.inbound.list_station import (
    PrefectureNotFound,
    StationOutput,
)
from app.application.station.ports.outbound.repository import StationRepository


class ListStationUseCase:
    def __init__(self, station_repo: StationRepository):
        self.station_repo = station_repo

    def list_stations(self, prec_no: int | None = None) -> list[StationOutput]:
        if prec_no is not None:
            stations = self.station_repo.get_by_prec_no(prec_no)
            if not stations:
                raise PrefectureNotFound("Prefecture not found")
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
