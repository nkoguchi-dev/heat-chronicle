from app.domain.station.model import Station
from app.domain.station.repository import StationRepository


class StationService:
    def __init__(self, station_repo: StationRepository):
        self.station_repo = station_repo

    def get_stations(self, prec_no: int | None = None) -> list[Station]:
        if prec_no is not None:
            return self.station_repo.get_by_prec_no(prec_no)
        return self.station_repo.get_all()
