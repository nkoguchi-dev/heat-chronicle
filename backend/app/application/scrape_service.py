import calendar
import logging
from datetime import date, datetime, timezone

from app.domain.fetch_freshness import FetchFreshnessPolicy, FetchStatus
from app.domain.schemas import MonthTemperatureResponse, TemperatureRecord
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import TemperatureRepository
from app.infrastructure.scraper.jma_client import JmaClient
from app.infrastructure.scraper.jma_parser import parse_daily_page

logger = logging.getLogger(__name__)


class ScrapeService:
    def __init__(
        self,
        station_repo: StationRepository,
        temp_repo: TemperatureRepository,
    ):
        self.station_repo = station_repo
        self.temp_repo = temp_repo

    async def fetch_month(
        self,
        station_id: int,
        year: int,
        month: int,
    ) -> MonthTemperatureResponse:
        """1ヶ月分のデータを取得して返す。キャッシュ済みならDBから返す。"""
        station = self.station_repo.get_by_id(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")

        # 未来の月はリクエストしない
        today = date.today()
        if year > today.year or (year == today.year and month > today.month):
            return MonthTemperatureResponse(year=year, month=month, records=[])

        # キャッシュ済みか確認
        fetched_months = self.temp_repo.get_fetched_months(station_id)
        fetched_at = fetched_months.get((year, month))

        policy = FetchFreshnessPolicy()
        status = policy.evaluate(year, month, fetched_at, datetime.now(timezone.utc))

        if status in (FetchStatus.UNFETCHED, FetchStatus.NEEDS_REFRESH):
            # JMAからスクレイプ
            client = JmaClient()
            try:
                html = await client.fetch_daily_page(
                    prec_no=station.prec_no,
                    block_no=station.block_no,
                    year=year,
                    month=month,
                    station_type=station.station_type,
                )

                records = parse_daily_page(html, year, month, station.station_type)

                if records:
                    db_records = [
                        {
                            "station_id": station_id,
                            "date": r.date.isoformat(),
                            "max_temp": r.max_temp,
                            "min_temp": r.min_temp,
                            "avg_temp": r.avg_temp,
                        }
                        for r in records
                    ]
                    self.temp_repo.bulk_insert_temperatures(db_records)

                self.temp_repo.insert_fetch_log(station_id, year, month)
            finally:
                await client.close()

        # DBからデータを取得して返す
        start_date = date(year, month, 1).isoformat()
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day).isoformat()

        db_records = self.temp_repo.get_by_station_and_range(
            station_id, start_date, end_date
        )

        return MonthTemperatureResponse(
            year=year,
            month=month,
            records=[
                TemperatureRecord(
                    date=r.date,
                    max_temp=r.max_temp,
                    min_temp=r.min_temp,
                    avg_temp=r.avg_temp,
                )
                for r in db_records
            ],
        )
