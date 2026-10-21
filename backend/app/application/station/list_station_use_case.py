from typing import assert_never

from app.application.station.ports.inbound.list_station import (
    ListStationStorageUnavailable,
    PrefectureNotFound,
    StationOutput,
)
from app.application.station.ports.outbound.repository import (
    StationRepository,
    StationsRead,
    StationStorageUnavailable,
)


class ListStationUseCase:
    def __init__(self, station_repo: StationRepository):
        self.station_repo = station_repo

    def list_stations(
        self, prec_no: int | None = None
    ) -> list[StationOutput] | ListStationStorageUnavailable:
        if prec_no is not None:
            match self.station_repo.get_by_prec_no(prec_no):
                case StationsRead(stations=stations):
                    pass
                case StationStorageUnavailable():
                    return ListStationStorageUnavailable()
                case unreachable_1:
                    assert_never(unreachable_1)
            if not stations:
                raise PrefectureNotFound("Prefecture not found")
        else:
            match self.station_repo.get_all():
                case StationsRead(stations=stations):
                    pass
                case StationStorageUnavailable():
                    return ListStationStorageUnavailable()
                case unreachable_2:
                    assert_never(unreachable_2)

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
