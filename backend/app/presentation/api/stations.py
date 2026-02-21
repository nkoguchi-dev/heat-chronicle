from fastapi import APIRouter

from app.application.temperature_service import TemperatureService
from app.di.container import SessionDep
from app.domain.schemas import StationResponse

router = APIRouter()


@router.get("/", response_model=list[StationResponse])
async def get_stations(session: SessionDep) -> list[StationResponse]:
    service = TemperatureService(session)
    return await service.get_all_stations()
