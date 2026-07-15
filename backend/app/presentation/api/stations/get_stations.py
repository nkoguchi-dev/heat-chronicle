from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.di.container import GetStationUseCaseDep

router = APIRouter()


class StationResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: int
    station_name: str
    prec_no: int
    block_no: str
    station_type: Literal["s", "a"]
    latitude: float | None = None
    longitude: float | None = None
    earliest_year: int | None = None


@router.get("/", response_model=list[StationResponse])
def get_stations(
    use_case: GetStationUseCaseDep,
    prec_no: int | None = None,
) -> list[StationResponse]:
    stations = use_case.get_stations(prec_no)
    return [
        StationResponse(
            id=station.id,
            station_name=station.station_name,
            prec_no=station.prec_no,
            block_no=station.block_no,
            station_type=station.station_type,
            latitude=station.latitude,
            longitude=station.longitude,
            earliest_year=station.earliest_year,
        )
        for station in stations
    ]
