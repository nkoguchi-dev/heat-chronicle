import calendar
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.domain.station.repository import StationRepository
from app.domain.temperature.data_source import TemperatureDataSource
from app.domain.temperature.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.temperature.repository import TemperatureRepository


@dataclass(frozen=True)
class FetchMonthTemperatureOutput:
    date: date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


class ScrapeService:
    def __init__(
        self,
        station_repo: StationRepository,
        temp_repo: TemperatureRepository,
        temperature_data_source: TemperatureDataSource,
    ):
        self.station_repo = station_repo
        self.temp_repo = temp_repo
        self.temperature_data_source = temperature_data_source

    async def fetch_month(
        self,
        station_id: int,
        year: int,
        month: int,
    ) -> list[FetchMonthTemperatureOutput]:
        """1ヶ月分のデータを取得して返す。キャッシュ済みならDBから返す。"""
        station = self.station_repo.get_by_id(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")

        # 未来の月はリクエストしない
        today = date.today()
        if year > today.year or (year == today.year and month > today.month):
            return []

        # キャッシュ済みか確認
        fetched_months = self.temp_repo.get_fetched_months(station_id)
        fetched_at = fetched_months.get((year, month))

        policy = FetchFreshnessPolicy()
        status = policy.evaluate(year, month, fetched_at, datetime.now(timezone.utc))

        if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
            records = await self.temperature_data_source.fetch_daily_temperatures(
                station,
                year,
                month,
            )

            if records:
                self.temp_repo.bulk_insert_temperatures(station_id, records)

            self.temp_repo.insert_fetch_log(station_id, year, month)

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
