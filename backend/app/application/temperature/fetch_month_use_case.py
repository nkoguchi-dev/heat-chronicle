import asyncio
import calendar
import logging
import sys
from datetime import date
from typing import assert_never

from app.application.shared.ports.outbound.clock import Clock
from app.application.station.ports.outbound.repository import (
    StationFound,
    StationMissing,
    StationRepository,
    StationStorageUnavailable,
)
from app.application.temperature.ports.inbound.errors import (
    FetchUnavailable as InboundFetchUnavailable,
)
from app.application.temperature.ports.inbound.errors import (
    InvalidTemperatureInput as InboundInvalidTemperatureInput,
)
from app.application.temperature.ports.inbound.errors import StationNotFound
from app.application.temperature.ports.inbound.fetch_month import (
    FetchMonthStorageUnavailable,
    FetchMonthTemperatureOutput,
)
from app.application.temperature.ports.outbound.data_source import (
    TemperatureDataSource,
    TemperaturesFetched,
    TemperatureSourceStorageUnavailable,
    TemperatureSourceUnavailable,
)
from app.application.temperature.ports.outbound.fetch_guard import (
    FetchGuard,
    GuardStorageUnavailable,
    GuardSucceeded,
    LeaseBusy,
    LeaseLost,
)
from app.application.temperature.ports.outbound.repository import (
    FetchedMonthsRead,
    TemperatureRepository,
    TemperaturesRead,
    TemperatureStorageUnavailable,
    TemperatureWriteSucceeded,
)
from app.domain.station.model import Station
from app.domain.temperature.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.temperature.input_policy import (
    InvalidTemperatureInput,
    observation_time,
    validate_month,
)

logger = logging.getLogger(__name__)

FETCH_BUDGET_SECONDS = 25


class FetchMonthUseCase:
    def __init__(
        self,
        station_repo: StationRepository,
        temp_repo: TemperatureRepository,
        temperature_data_source: TemperatureDataSource,
        fetch_guard: FetchGuard,
        clock: Clock,
    ):
        self.station_repo = station_repo
        self.temp_repo = temp_repo
        self.temperature_data_source = temperature_data_source
        self.fetch_guard = fetch_guard
        self.clock = clock

    async def fetch_month(
        self, station_id: int, year: int, month: int
    ) -> list[FetchMonthTemperatureOutput] | FetchMonthStorageUnavailable:
        try:
            return await self._fetch_month(station_id, year, month)
        except InvalidTemperatureInput as exc:
            raise InboundInvalidTemperatureInput(str(exc)) from exc

    async def _fetch_month(
        self,
        station_id: int,
        year: int,
        month: int,
    ) -> list[FetchMonthTemperatureOutput] | FetchMonthStorageUnavailable:
        """1ヶ月分のデータを取得して返す。キャッシュ済みならDBから返す。"""
        now = observation_time(self.clock.now())
        match self.station_repo.get_by_id(station_id):
            case StationFound(station=station):
                pass
            case StationMissing():
                raise StationNotFound(f"Station {station_id} not found")
            case StationStorageUnavailable():
                return FetchMonthStorageUnavailable()
            case unreachable_1:
                assert_never(unreachable_1)

        validate_month(station, year, month, now)

        # キャッシュ済みか確認
        match self.temp_repo.get_fetched_months(station_id):
            case FetchedMonthsRead(months=fetched_months):
                pass
            case TemperatureStorageUnavailable():
                return FetchMonthStorageUnavailable()
            case unreachable_2:
                assert_never(unreachable_2)
        fetched_at = fetched_months.get((year, month))

        policy = FetchFreshnessPolicy()
        status = policy.evaluate(year, month, fetched_at, self.clock.now())

        if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
            match self.fetch_guard.acquire():
                case GuardSucceeded():
                    pass
                case LeaseBusy():
                    # Temporary Inbound bridge; removed in #250.
                    raise InboundFetchUnavailable()
                case GuardStorageUnavailable():
                    return FetchMonthStorageUnavailable()
                case unreachable_acquire:
                    assert_never(unreachable_acquire)
            result: FetchMonthStorageUnavailable | None = None
            try:
                result = await self._refresh(station_id, year, month, station, policy)
            finally:
                active_error = sys.exception()
                try:
                    match self.fetch_guard.release():
                        case GuardSucceeded():
                            pass
                        case GuardStorageUnavailable():
                            logger.warning("lease_release_unavailable")
                            if active_error is None and result is None:
                                result = FetchMonthStorageUnavailable()
                        case unreachable_release:
                            assert_never(unreachable_release)
                except BaseException:
                    if active_error is None:
                        raise
                    logger.warning("lease_release_failed_during_exception")
            if result is not None:
                return result

        # DBからデータを取得して返す
        start_date = date(year, month, 1).isoformat()
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day).isoformat()

        match self.temp_repo.get_by_station_and_range(station_id, start_date, end_date):
            case TemperaturesRead(records=temperature_records):
                pass
            case TemperatureStorageUnavailable():
                return FetchMonthStorageUnavailable()
            case unreachable_6:
                assert_never(unreachable_6)

        return [
            FetchMonthTemperatureOutput(
                date=record.date,
                max_temp=record.max_temp,
                min_temp=record.min_temp,
                avg_temp=record.avg_temp,
            )
            for record in temperature_records
        ]

    async def _refresh(
        self,
        station_id: int,
        year: int,
        month: int,
        station: Station,
        policy: FetchFreshnessPolicy,
    ) -> FetchMonthStorageUnavailable | None:
        deadline = self.clock.monotonic() + FETCH_BUDGET_SECONDS
        try:
            async with asyncio.timeout(FETCH_BUDGET_SECONDS):
                match self.temp_repo.get_fetched_months(station_id):
                    case FetchedMonthsRead(months=refreshed):
                        pass
                    case TemperatureStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_read:
                        assert_never(unreachable_read)
                status = policy.evaluate(
                    year, month, refreshed.get((year, month)), self.clock.now()
                )
                if status not in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
                    return None
                match await self.temperature_data_source.fetch_daily_temperatures(
                    station, year, month
                ):
                    case TemperaturesFetched(records=records):
                        pass
                    case TemperatureSourceUnavailable():
                        raise InboundFetchUnavailable()
                    case TemperatureSourceStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_source:
                        assert_never(unreachable_source)
                if self.clock.monotonic() >= deadline:
                    raise InboundFetchUnavailable()
                owner_failure = self._check_owner()
                if owner_failure is not None:
                    return owner_failure
                if records:
                    match self.temp_repo.bulk_insert_temperatures(station_id, records):
                        case TemperatureWriteSucceeded():
                            pass
                        case TemperatureStorageUnavailable():
                            return FetchMonthStorageUnavailable()
                        case unreachable_write:
                            assert_never(unreachable_write)
                owner_failure = self._check_owner()
                if owner_failure is not None:
                    return owner_failure
                match self.temp_repo.insert_fetch_log(station_id, year, month):
                    case TemperatureWriteSucceeded():
                        return None
                    case TemperatureStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_log:
                        assert_never(unreachable_log)
        except TimeoutError as exc:
            raise InboundFetchUnavailable() from exc

    def _check_owner(self) -> FetchMonthStorageUnavailable | None:
        match self.fetch_guard.check_owner():
            case GuardSucceeded():
                return None
            case LeaseLost():
                raise InboundFetchUnavailable()
            case GuardStorageUnavailable():
                return FetchMonthStorageUnavailable()
            case unreachable:
                assert_never(unreachable)
