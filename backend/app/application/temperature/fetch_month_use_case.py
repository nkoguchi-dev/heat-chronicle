import asyncio
import calendar
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
from app.application.temperature.ports.outbound.data_source import TemperatureDataSource
from app.application.temperature.ports.outbound.fetch_guard import (
    FetchGuard,
    FetchUnavailable,
)
from app.application.temperature.ports.outbound.repository import (
    FetchedMonthsRead,
    TemperatureRepository,
    TemperaturesRead,
    TemperatureStorageUnavailable,
    TemperatureWriteSucceeded,
)
from app.domain.temperature.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.temperature.input_policy import (
    InvalidTemperatureInput,
    observation_time,
    validate_month,
)

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
        except FetchUnavailable as exc:
            raise InboundFetchUnavailable() from exc

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
            self.fetch_guard.acquire()
            deadline = self.clock.monotonic() + FETCH_BUDGET_SECONDS
            try:
                async with asyncio.timeout(FETCH_BUDGET_SECONDS):
                    # Another owner may have populated the cache since the first read.
                    match self.temp_repo.get_fetched_months(station_id):
                        case FetchedMonthsRead(months=refreshed):
                            pass
                        case TemperatureStorageUnavailable():
                            return FetchMonthStorageUnavailable()
                        case unreachable_3:
                            assert_never(unreachable_3)
                    status = policy.evaluate(
                        year,
                        month,
                        refreshed.get((year, month)),
                        self.clock.now(),
                    )
                    if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
                        records = (
                            await self.temperature_data_source.fetch_daily_temperatures(
                                station, year, month
                            )
                        )
                        if self.clock.monotonic() >= deadline:
                            raise FetchUnavailable()
                        self.fetch_guard.check_owner()
                        if records:
                            match self.temp_repo.bulk_insert_temperatures(
                                station_id, records
                            ):
                                case TemperatureWriteSucceeded():
                                    pass
                                case TemperatureStorageUnavailable():
                                    return FetchMonthStorageUnavailable()
                                case unreachable_4:
                                    assert_never(unreachable_4)
                        self.fetch_guard.check_owner()
                        match self.temp_repo.insert_fetch_log(station_id, year, month):
                            case TemperatureWriteSucceeded():
                                pass
                            case TemperatureStorageUnavailable():
                                return FetchMonthStorageUnavailable()
                            case unreachable_5:
                                assert_never(unreachable_5)
            except (TimeoutError, RuntimeError) as exc:
                raise FetchUnavailable() from exc
            finally:
                self.fetch_guard.release()

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
