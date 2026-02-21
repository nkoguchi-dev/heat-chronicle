from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas import (
    StationResponse,
    TemperatureMetadata,
    TemperatureRecord,
    TemperatureResponse,
)
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import (
    TemperatureRepository,
)


class TemperatureService:
    def __init__(self, session: AsyncSession):
        self.station_repo = StationRepository(session)
        self.temp_repo = TemperatureRepository(session)

    async def get_all_stations(self) -> list[StationResponse]:
        stations = await self.station_repo.get_all()
        return [
            StationResponse(
                id=s.id,
                station_name=s.station_name,
                prec_no=s.prec_no,
                block_no=s.block_no,
                station_type=s.station_type,
                latitude=s.latitude,
                longitude=s.longitude,
            )
            for s in stations
        ]

    async def get_temperature_data(
        self, station_id: int, start_year: int, end_year: int
    ) -> TemperatureResponse:
        station = await self.station_repo.get_by_id(station_id)
        if station is None:
            raise ValueError(f"Station {station_id} not found")

        start_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31)

        records = await self.temp_repo.get_by_station_and_range(
            station_id, start_date, end_date
        )
        fetched_months = await self.temp_repo.get_fetched_months(station_id)

        # Determine which months in range have been fetched
        fetched_set = {(y, m) for y, m in fetched_months}
        required_months = []
        for y in range(end_year, start_year - 1, -1):
            for m in range(12, 0, -1):
                if (y, m) not in fetched_set:
                    required_months.append((y, m))

        fetched_month_strs = [f"{y}-{m:02d}" for y, m in fetched_months]

        data = [
            TemperatureRecord(
                date=r.date,
                max_temp=r.max_temp,
                min_temp=r.min_temp,
                avg_temp=r.avg_temp,
            )
            for r in records
        ]

        metadata = TemperatureMetadata(
            station_id=station_id,
            station_name=station.station_name,
            start_year=start_year,
            end_year=end_year,
            total_records=len(data),
            fetched_months=fetched_month_strs,
            fetching_required=len(required_months) > 0,
        )

        return TemperatureResponse(metadata=metadata, data=data)
