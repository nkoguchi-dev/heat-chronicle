from app.domain.station.model import Station
from app.domain.station.repository import StationRepository


class StationService:
    def __init__(self, station_repo: StationRepository):
        self.station_repo = station_repo

    def get_all(self) -> list[Station]:
        return self.station_repo.get_all()

    def get_by_prec_no(self, prec_no: int) -> list[Station]:
        return self.station_repo.get_by_prec_no(prec_no)
