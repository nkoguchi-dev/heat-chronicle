import json
import logging
from collections.abc import AsyncGenerator
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.tables import Station
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import (
    TemperatureRepository,
)
from app.infrastructure.scraper.jma_client import JmaClient
from app.infrastructure.scraper.jma_parser import parse_daily_page

logger = logging.getLogger(__name__)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ScrapeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.station_repo = StationRepository(session)
        self.temp_repo = TemperatureRepository(session)

    async def stream_fetch(
        self,
        station_id: int,
        start_year: int,
        end_year: int,
    ) -> AsyncGenerator[str, None]:
        station = await self.station_repo.get_by_id(station_id)
        if station is None:
            yield _sse_event("error", {"message": f"Station {station_id} not found"})
            return

        # Calculate required months
        fetched = await self.temp_repo.get_fetched_months(station_id)
        fetched_set = set(fetched)

        months_to_fetch: list[tuple[int, int]] = []
        for y in range(start_year, end_year + 1):
            for m in range(1, 13):
                if (y, m) not in fetched_set:
                    # Skip future months
                    today = date.today()
                    if y > today.year or (y == today.year and m > today.month):
                        continue
                    months_to_fetch.append((y, m))

        total = len(months_to_fetch)
        if total == 0:
            yield _sse_event("complete", {"message": "All data already cached", "total_records": 0})
            return

        client = JmaClient()
        completed = 0
        total_records = 0

        try:
            for year, month in months_to_fetch:
                try:
                    yield _sse_event(
                        "progress",
                        {
                            "year": year,
                            "month": month,
                            "completed": completed,
                            "total": total,
                        },
                    )

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
                                "date": r.date,
                                "max_temp": r.max_temp,
                                "min_temp": r.min_temp,
                                "avg_temp": r.avg_temp,
                            }
                            for r in records
                        ]
                        await self.temp_repo.bulk_insert_temperatures(db_records)

                    await self.temp_repo.insert_fetch_log(station_id, year, month)
                    await self.session.commit()

                    completed += 1
                    total_records += len(records)

                    # Send data event with the records for this month
                    yield _sse_event(
                        "data",
                        {
                            "year": year,
                            "month": month,
                            "records": [
                                {
                                    "date": r.date.isoformat(),
                                    "max_temp": r.max_temp,
                                    "min_temp": r.min_temp,
                                    "avg_temp": r.avg_temp,
                                }
                                for r in records
                            ],
                        },
                    )

                except Exception as e:
                    logger.exception("Error fetching %d-%02d for station %d", year, month, station_id)
                    yield _sse_event(
                        "error",
                        {
                            "message": f"Error fetching {year}-{month:02d}: {e}",
                            "year": year,
                            "month": month,
                        },
                    )
                    # Continue with next month

            yield _sse_event(
                "complete",
                {"message": "Fetch complete", "total_records": total_records},
            )
        finally:
            await client.close()
