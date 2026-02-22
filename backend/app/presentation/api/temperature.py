from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.application.scrape_service import ScrapeService
from app.application.temperature_service import TemperatureService
from app.di.container import StationRepoDep, TempRepoDep
from app.domain.schemas import TemperatureResponse

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


@router.get("/{station_id}/stream")
async def stream_temperature(
    station_id: int,
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    start_year: int = Query(default=1975),
    end_year: int = Query(default_factory=lambda: datetime.now().year),
) -> StreamingResponse:
    service = ScrapeService(station_repo, temp_repo)

    return StreamingResponse(
        service.stream_fetch(station_id, start_year, end_year),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
