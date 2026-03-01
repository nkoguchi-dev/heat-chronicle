from datetime import date

from app.domain.schemas import StationResponse, TemperatureMetadata, TemperatureResponse
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import TemperatureRepository

CHUNK_SIZE = 50
FALLBACK_START_YEAR = 1975


class TemperatureService:
    def __init__(
        self,
        station_repo: StationRepository,
        temp_repo: TemperatureRepository,
    ):
        self.station_repo = station_repo
        self.temp_repo = temp_repo

    def get_all_stations(self) -> list[StationResponse]:
        return self.station_repo.get_all()

    def get_stations_by_prec_no(self, prec_no: int) -> list[StationResponse]:
        return self.station_repo.get_by_prec_no(prec_no)

    def get_temperature_data(
        self, station_id: int, end_year: int
    ) -> TemperatureResponse:
        station = self.station_repo.get_by_id(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")

        effective_earliest = station.earliest_year or FALLBACK_START_YEAR
        start_year = max(effective_earliest, end_year - CHUNK_SIZE + 1)

        has_older_data = start_year > effective_earliest
        next_end_year = start_year - 1 if has_older_data else None

        start_date = date(start_year, 1, 1).isoformat()
        end_date = date(end_year, 12, 31).isoformat()

        records = self.temp_repo.get_by_station_and_range(
            station_id, start_date, end_date
        )
        fetched_months = self.temp_repo.get_fetched_months(station_id)

        fetched_set = {(y, m) for y, m in fetched_months}
        required_months = []
        for y in range(end_year, start_year - 1, -1):
            for m in range(12, 0, -1):
                if (y, m) not in fetched_set:
                    required_months.append((y, m))

        fetched_month_strs = [f"{y}-{m:02d}" for y, m in fetched_months]

        metadata = TemperatureMetadata(
            station_id=station_id,
            station_name=station.station_name,
            start_year=start_year,
            end_year=end_year,
            total_records=len(records),
            fetched_months=fetched_month_strs,
            fetching_required=len(required_months) > 0,
            has_older_data=has_older_data,
            next_end_year=next_end_year,
        )

        return TemperatureResponse(metadata=metadata, data=records)
