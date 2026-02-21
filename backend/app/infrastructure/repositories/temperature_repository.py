from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.tables import DailyTemperature, FetchLog


class TemperatureRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_station_and_range(
        self, station_id: int, start_date: date, end_date: date
    ) -> list[DailyTemperature]:
        result = await self.session.execute(
            select(DailyTemperature)
            .where(
                DailyTemperature.station_id == station_id,
                DailyTemperature.date >= start_date,
                DailyTemperature.date <= end_date,
            )
            .order_by(DailyTemperature.date)
        )
        return list(result.scalars().all())

    async def get_fetched_months(
        self, station_id: int
    ) -> list[tuple[int, int]]:
        result = await self.session.execute(
            select(FetchLog.year, FetchLog.month)
            .where(FetchLog.station_id == station_id)
            .order_by(FetchLog.year, FetchLog.month)
        )
        return list(result.tuples().all())

    async def bulk_insert_temperatures(
        self,
        records: list[dict],
    ) -> None:
        if not records:
            return
        stmt = pg_insert(DailyTemperature).values(records)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_daily_temp_station_date"
        )
        await self.session.execute(stmt)

    async def insert_fetch_log(
        self, station_id: int, year: int, month: int
    ) -> None:
        stmt = pg_insert(FetchLog).values(
            station_id=station_id, year=year, month=month
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_fetch_log_station_year_month"
        )
        await self.session.execute(stmt)
