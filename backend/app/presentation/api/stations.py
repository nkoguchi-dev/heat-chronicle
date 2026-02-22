from fastapi import APIRouter

from app.application.temperature_service import TemperatureService
from app.di.container import SessionDep
from app.domain.schemas import StationResponse

router = APIRouter()


@router.get("/", response_model=list[StationResponse])
async def get_stations(
    session: SessionDep, prec_no: int | None = None
) -> list[StationResponse]:
    service = TemperatureService(session)
    if prec_no is not None:
        return await service.get_stations_by_prec_no(prec_no)
    return await service.get_all_stations()
