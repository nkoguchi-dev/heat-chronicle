from datetime import date, datetime
from typing import assert_never

from app.application.shared.ports.outbound.clock import Clock
from app.application.station.ports.outbound.repository import (
    StationFound,
    StationMissing,
    StationRepository,
    StationStorageUnavailable,
)
from app.application.temperature.ports.inbound.errors import (
    InvalidTemperatureInput,
    StationNotFound,
)
from app.application.temperature.ports.inbound.get_temperature import (
    GetTemperatureDataOutput,
    GetTemperatureStorageUnavailable,
    TemperatureMetadataOutput,
    TemperatureRecordOutput,
)
from app.application.temperature.ports.outbound.repository import (
    FetchedMonthsRead,
    TemperatureRepository,
    TemperaturesRead,
    TemperatureStorageUnavailable,
)
from app.domain.temperature.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.temperature.input_policy import (
    InvalidTemperatureInput as DomainInvalidTemperatureInput,
)
from app.domain.temperature.input_policy import (
    earliest_year,
    observation_time,
    validate_year,
)

CHUNK_SIZE = 50


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


class GetTemperatureUseCase:
    def __init__(
        self,
        station_repo: StationRepository,
        temp_repo: TemperatureRepository,
        clock: Clock,
    ):
        self.station_repo = station_repo
        self.temp_repo = temp_repo
        self.clock = clock

    def get_temperature_data(
        self, station_id: int, end_year: int | None
    ) -> GetTemperatureDataOutput | GetTemperatureStorageUnavailable:
        now = self.clock.now()
        now_jst = observation_time(now)
        match self.station_repo.get_by_id(station_id):
            case StationFound(station=station):
                pass
            case StationMissing():
                raise StationNotFound(f"Station {station_id} not found")
            case StationStorageUnavailable():
                return GetTemperatureStorageUnavailable()
            case unreachable_1:
                assert_never(unreachable_1)

        end_year = now_jst.year if end_year is None else end_year
        try:
            validate_year(station, end_year, now_jst)
        except DomainInvalidTemperatureInput as exc:
            raise InvalidTemperatureInput(str(exc)) from exc
        effective_earliest = earliest_year(station)
        start_year = max(effective_earliest, end_year - CHUNK_SIZE + 1)

        has_older_data = start_year > effective_earliest
        next_end_year = start_year - 1 if has_older_data else None

        start_date, end_date = _build_date_range(start_year, end_year)
        match self.temp_repo.get_by_station_and_range(station_id, start_date, end_date):
            case TemperaturesRead(records=records):
                pass
            case TemperatureStorageUnavailable():
                return GetTemperatureStorageUnavailable()
            case unreachable_2:
                assert_never(unreachable_2)
        match self.temp_repo.get_fetched_months(station_id):
            case FetchedMonthsRead(months=fetched_months):
                pass
            case TemperatureStorageUnavailable():
                return GetTemperatureStorageUnavailable()
            case unreachable_3:
                assert_never(unreachable_3)

        policy = FetchFreshnessPolicy()
        required_months = _find_missing_months(
            policy, start_year, end_year, fetched_months, now
        )

        fetched_month_strs = [
            f"{y}-{m:02d}"
            for (y, m), fetched_at in fetched_months.items()
            if policy.evaluate(y, m, fetched_at, now)
            in (FetchStatus.FINALIZED, FetchStatus.TEMPORARILY_CACHED)
        ]

        metadata = TemperatureMetadataOutput(
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

        data = [
            TemperatureRecordOutput(
                date=record.date,
                max_temp=record.max_temp,
                min_temp=record.min_temp,
                avg_temp=record.avg_temp,
            )
            for record in records
        ]

        return GetTemperatureDataOutput(metadata=metadata, data=data)
