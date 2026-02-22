from fastapi import APIRouter

from app.application.temperature_service import TemperatureService
from app.di.container import StationRepoDep, TempRepoDep
from app.domain.schemas import StationResponse

router = APIRouter()


@router.get("/", response_model=list[StationResponse])
def get_stations(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    prec_no: int | None = None,
) -> list[StationResponse]:
    service = TemperatureService(station_repo, temp_repo)
    if prec_no is not None:
        return service.get_stations_by_prec_no(prec_no)
    return service.get_all_stations()
