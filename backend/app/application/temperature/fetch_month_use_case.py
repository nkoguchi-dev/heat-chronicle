import asyncio
import calendar
from dataclasses import dataclass
from datetime import date

from app.application.shared.ports.outbound.clock import Clock
from app.application.station.ports.outbound.repository import StationRepository
from app.application.temperature.ports.outbound.repository import TemperatureRepository
from app.domain.temperature.data_source import TemperatureDataSource
from app.domain.temperature.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.temperature.fetch_guard import FetchGuard, FetchUnavailable
from app.domain.temperature.input_policy import observation_time, validate_month

FETCH_BUDGET_SECONDS = 25


@dataclass(frozen=True)
class FetchMonthTemperatureOutput:
    date: date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


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
        self,
        station_id: int,
        year: int,
        month: int,
    ) -> list[FetchMonthTemperatureOutput]:
        """1ヶ月分のデータを取得して返す。キャッシュ済みならDBから返す。"""
        now = observation_time(self.clock.now())
        station = self.station_repo.get_by_id(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")

        validate_month(station, year, month, now)

        # キャッシュ済みか確認
        fetched_months = self.temp_repo.get_fetched_months(station_id)
        fetched_at = fetched_months.get((year, month))

        policy = FetchFreshnessPolicy()
        status = policy.evaluate(year, month, fetched_at, self.clock.now())

        if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
            self.fetch_guard.acquire()
            deadline = self.clock.monotonic() + FETCH_BUDGET_SECONDS
            try:
                async with asyncio.timeout(FETCH_BUDGET_SECONDS):
                    # Another owner may have populated the cache since the first read.
                    refreshed = self.temp_repo.get_fetched_months(station_id)
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
                            self.temp_repo.bulk_insert_temperatures(station_id, records)
                        self.fetch_guard.check_owner()
                        self.temp_repo.insert_fetch_log(station_id, year, month)
            except (TimeoutError, RuntimeError) as exc:
                raise FetchUnavailable() from exc
            finally:
                self.fetch_guard.release()

        # DBからデータを取得して返す
        start_date = date(year, month, 1).isoformat()
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day).isoformat()

        temperature_records = self.temp_repo.get_by_station_and_range(
            station_id, start_date, end_date
        )

        return [
            FetchMonthTemperatureOutput(
                date=record.date,
                max_temp=record.max_temp,
                min_temp=record.min_temp,
                avg_temp=record.avg_temp,
            )
            for record in temperature_records
        ]
