from datetime import date, datetime, timezone

from app.domain.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.schemas import StationResponse, TemperatureMetadata, TemperatureResponse
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import TemperatureRepository

CHUNK_SIZE = 50
FALLBACK_START_YEAR = 1975


def _build_date_range(start_year: int, end_year: int) -> tuple[str, str]:
    start_date = date(start_year, 1, 1).isoformat()
    end_date = date(end_year, 12, 31).isoformat()
    return start_date, end_date


def _find_missing_months(
    policy: FetchFreshnessPolicy,
    start_year: int,
    end_year: int,
    fetched_months: dict[tuple[int, int], datetime],
    now: datetime,
) -> list[tuple[int, int]]:
    required = []
    for y in range(end_year, start_year - 1, -1):
        for m in range(12, 0, -1):
            fetched_at = fetched_months.get((y, m))
            status = policy.evaluate(y, m, fetched_at, now)
            if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
                required.append((y, m))
    return required


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

        start_date, end_date = _build_date_range(start_year, end_year)
        records = self.temp_repo.get_by_station_and_range(
            station_id, start_date, end_date
        )
        fetched_months = self.temp_repo.get_fetched_months(station_id)

        policy = FetchFreshnessPolicy()
        now = datetime.now(timezone.utc)
        required_months = _find_missing_months(
            policy, start_year, end_year, fetched_months, now
        )

        fetched_month_strs = [
            f"{y}-{m:02d}"
            for (y, m), fetched_at in fetched_months.items()
            if policy.evaluate(y, m, fetched_at, now)
            in (FetchStatus.FINALIZED, FetchStatus.TEMPORARILY_CACHED)
        ]

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
