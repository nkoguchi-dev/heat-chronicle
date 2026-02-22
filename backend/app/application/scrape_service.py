import asyncio
import logging
import uuid
from datetime import date

from app.infrastructure.repositories.job_repository import JobRepository
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import (
    TemperatureRepository,
)
from app.infrastructure.scraper.jma_client import JmaClient
from app.infrastructure.scraper.jma_parser import parse_daily_page

logger = logging.getLogger(__name__)


class ScrapeService:
    def __init__(
        self,
        station_repo: StationRepository,
        temp_repo: TemperatureRepository,
        job_repo: JobRepository,
    ):
        self.station_repo = station_repo
        self.temp_repo = temp_repo
        self.job_repo = job_repo

    def create_job(
        self,
        station_id: int,
        start_year: int,
        end_year: int,
    ) -> dict:
        active = self.job_repo.find_active_job(station_id)
        if active:
            return active

        station = self.station_repo.get_by_id(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")

        fetched = self.temp_repo.get_fetched_months(station_id)
        fetched_set = set(fetched)

        months_to_fetch: list[tuple[int, int]] = []
        for y in range(end_year, start_year - 1, -1):
            for m in range(12, 0, -1):
                if (y, m) not in fetched_set:
                    today = date.today()
                    if y > today.year or (y == today.year and m > today.month):
                        continue
                    months_to_fetch.append((y, m))

        total = len(months_to_fetch)
        job_id = str(uuid.uuid4())
        job = self.job_repo.create_job(job_id, station_id, total)
        return job

    async def execute_job(self, job_id: str) -> None:
        job = self.job_repo.get_job(job_id)
        if job is None:
            logger.error("Job %s not found", job_id)
            return

        station_id = int(job["station_id"])
        station = await asyncio.to_thread(
            self.station_repo.get_by_id, station_id
        )
        if station is None:
            self.job_repo.fail_job(job_id, f"Station {station_id} not found")
            return

        fetched = await asyncio.to_thread(
            self.temp_repo.get_fetched_months, station_id
        )
        fetched_set = set(fetched)

        total = int(job["total"])
        if total == 0:
            self.job_repo.complete_job(job_id, 0)
            return

        months_to_fetch: list[tuple[int, int]] = []
        today = date.today()
        for y in range(today.year, 1974, -1):
            for m in range(12, 0, -1):
                if (y, m) not in fetched_set:
                    if y > today.year or (y == today.year and m > today.month):
                        continue
                    months_to_fetch.append((y, m))

        client = JmaClient()
        completed = 0
        total_records = 0

        try:
            for year, month in months_to_fetch:
                try:
                    html = await client.fetch_daily_page(
                        prec_no=station.prec_no,
                        block_no=station.block_no,
                        year=year,
                        month=month,
                        station_type=station.station_type,
                    )

                    records = parse_daily_page(
                        html, year, month, station.station_type
                    )

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
                        await asyncio.to_thread(
                            self.temp_repo.bulk_insert_temperatures, db_records
                        )

                    await asyncio.to_thread(
                        self.temp_repo.insert_fetch_log, station_id, year, month
                    )

                    completed += 1
                    total_records += len(records)

                    await asyncio.to_thread(
                        self.job_repo.update_progress,
                        job_id,
                        completed,
                        year,
                        month,
                        len(records),
                    )

                except Exception:
                    logger.exception(
                        "Error fetching %d-%02d for station %d",
                        year,
                        month,
                        station_id,
                    )
                    completed += 1

            await asyncio.to_thread(
                self.job_repo.complete_job, job_id, total_records
            )
        except Exception as e:
            logger.exception("Job %s failed", job_id)
            await asyncio.to_thread(
                self.job_repo.fail_job, job_id, str(e)
            )
        finally:
            await client.close()

    def get_job_status(self, job_id: str) -> dict | None:
        return self.job_repo.get_job(job_id)
