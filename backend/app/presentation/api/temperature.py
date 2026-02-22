from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.application.scrape_service import ScrapeService
from app.application.temperature_service import TemperatureService
from app.di.container import StationRepoDep, TempRepoDep
from app.domain.schemas import (
    MonthTemperatureResponse,
    TemperatureResponse,
)

router = APIRouter()


@router.get("/{station_id}", response_model=TemperatureResponse)
def get_temperature(
    station_id: int,
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    start_year: int = Query(default=1975),
    end_year: int = Query(default_factory=lambda: datetime.now().year),
) -> TemperatureResponse:
    try:
        service = TemperatureService(station_repo, temp_repo)
        return service.get_temperature_data(station_id, start_year, end_year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{station_id}/fetch-month", response_model=MonthTemperatureResponse
)
async def fetch_month(
    station_id: int,
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    year: int = Query(...),
    month: int = Query(...),
) -> MonthTemperatureResponse:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="month must be 1-12")

    service = ScrapeService(station_repo, temp_repo)
    try:
        return await service.fetch_month(station_id, year, month)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
