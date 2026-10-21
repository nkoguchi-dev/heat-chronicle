import asyncio
import calendar
import logging
from dataclasses import dataclass
from datetime import date
from typing import assert_never

from app.application.shared.ports.outbound.clock import Clock
from app.application.station.ports.outbound.repository import (
    StationFound,
    StationMissing,
    StationRepository,
    StationStorageUnavailable,
)
from app.application.temperature.ports.inbound.fetch_month import (
    FetchMonthInvalidPeriod,
    FetchMonthNotFound,
    FetchMonthResult,
    FetchMonthStorageUnavailable,
    FetchMonthTemperatureOutput,
    FetchMonthUnavailable,
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
    InvalidObservationPeriod,
    ObservationPeriodValid,
    observation_time,
    validate_month,
)

logger = logging.getLogger(__name__)

FETCH_BUDGET_SECONDS = 25


@dataclass(frozen=True)
class _RefreshSucceeded:
    pass


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
    ) -> (
        FetchMonthResult
        | FetchMonthNotFound
        | FetchMonthInvalidPeriod
        | FetchMonthStorageUnavailable
        | FetchMonthUnavailable
    ):
        """1ヶ月分のデータを取得して返す。キャッシュ済みならDBから返す。"""
        now = observation_time(self.clock.now())
        match self.station_repo.get_by_id(station_id):
            case StationFound(station=station):
                pass
            case StationMissing():
                return FetchMonthNotFound(station_id)
            case StationStorageUnavailable():
                return FetchMonthStorageUnavailable()
            case unreachable_1:
                assert_never(unreachable_1)

        match validate_month(station, year, month, now):
            case ObservationPeriodValid():
                pass
            case InvalidObservationPeriod(detail=detail):
                return FetchMonthInvalidPeriod(detail)
            case unreachable_period:
                assert_never(unreachable_period)

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
                    return FetchMonthUnavailable()
                case GuardStorageUnavailable():
                    return FetchMonthStorageUnavailable()
                case unreachable_acquire:
                    assert_never(unreachable_acquire)
            result: (
                _RefreshSucceeded | FetchMonthStorageUnavailable | FetchMonthUnavailable
            ) = _RefreshSucceeded()
            active_error = False
            try:
                result = await self._refresh(station_id, year, month, station, policy)
            except BaseException:
                active_error = True
                raise
            finally:
                try:
                    match self.fetch_guard.release():
                        case GuardSucceeded():
                            pass
                        case GuardStorageUnavailable():
                            logger.warning("lease_release_unavailable")
                            if not active_error and isinstance(
                                result, _RefreshSucceeded
                            ):
                                result = FetchMonthStorageUnavailable()
                        case unreachable_release:
                            assert_never(unreachable_release)
                except BaseException:
                    if not active_error:
                        raise
                    logger.warning("lease_release_failed_during_exception")
            match result:
                case _RefreshSucceeded():
                    pass
                case (
                    FetchMonthUnavailable() | FetchMonthStorageUnavailable() as failure
                ):
                    return failure
                case unreachable_refresh:
                    assert_never(unreachable_refresh)

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

        return FetchMonthResult(
            [
                FetchMonthTemperatureOutput(
                    date=record.date,
                    max_temp=record.max_temp,
                    min_temp=record.min_temp,
                    avg_temp=record.avg_temp,
                )
                for record in temperature_records
            ]
        )

    async def _refresh(
        self,
        station_id: int,
        year: int,
        month: int,
        station: Station,
        policy: FetchFreshnessPolicy,
    ) -> _RefreshSucceeded | FetchMonthStorageUnavailable | FetchMonthUnavailable:
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
                    return _RefreshSucceeded()
                match await self.temperature_data_source.fetch_daily_temperatures(
                    station, year, month
                ):
                    case TemperaturesFetched(records=records):
                        pass
                    case TemperatureSourceUnavailable():
                        return FetchMonthUnavailable()
                    case TemperatureSourceStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_source:
                        assert_never(unreachable_source)
                if self.clock.monotonic() >= deadline:
                    return FetchMonthUnavailable()
                match self.fetch_guard.check_owner():
                    case GuardSucceeded():
                        pass
                    case LeaseLost():
                        return FetchMonthUnavailable()
                    case GuardStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_before_write:
                        assert_never(unreachable_before_write)
                if records:
                    match self.temp_repo.bulk_insert_temperatures(station_id, records):
                        case TemperatureWriteSucceeded():
                            pass
                        case TemperatureStorageUnavailable():
                            return FetchMonthStorageUnavailable()
                        case unreachable_write:
                            assert_never(unreachable_write)
                match self.fetch_guard.check_owner():
                    case GuardSucceeded():
                        pass
                    case LeaseLost():
                        return FetchMonthUnavailable()
                    case GuardStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_before_log:
                        assert_never(unreachable_before_log)
                match self.temp_repo.insert_fetch_log(station_id, year, month):
                    case TemperatureWriteSucceeded():
                        return _RefreshSucceeded()
                    case TemperatureStorageUnavailable():
                        return FetchMonthStorageUnavailable()
                    case unreachable_log:
                        assert_never(unreachable_log)
        except TimeoutError:
            return FetchMonthUnavailable()
