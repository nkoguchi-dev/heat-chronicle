from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.application.scrape_service import ScrapeService
from app.application.temperature_service import TemperatureService
from app.di.container import ManualSessionDep, SessionDep
from app.domain.schemas import TemperatureResponse

router = APIRouter()


@router.get("/{station_id}", response_model=TemperatureResponse)
async def get_temperature(
    station_id: int,
    session: SessionDep,
    start_year: int = Query(default=1975),
    end_year: int = Query(default_factory=lambda: datetime.now().year),
) -> TemperatureResponse:
    try:
        service = TemperatureService(session)
        return await service.get_temperature_data(station_id, start_year, end_year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{station_id}/stream")
async def stream_temperature(
    station_id: int,
    session: ManualSessionDep,
    start_year: int = Query(default=1975),
    end_year: int = Query(default_factory=lambda: datetime.now().year),
) -> StreamingResponse:
    service = ScrapeService(session)

    return StreamingResponse(
        service.stream_fetch(station_id, start_year, end_year),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
