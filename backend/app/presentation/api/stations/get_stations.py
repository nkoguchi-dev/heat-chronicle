from typing import Annotated, Literal, assert_never

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.application.station.ports.inbound.list_station import (
    ListStationPort,
    ListStationStorageUnavailable,
)
from app.presentation.api.shared.dependencies import get_station_port
from app.presentation.api.shared.internal_server_error import storage_error_response

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
    use_case: Annotated[ListStationPort, Depends(get_station_port)],
    prec_no: int | None = None,
) -> list[StationResponse] | JSONResponse:
    try:
        match use_case.list_stations(prec_no):
            case ListStationStorageUnavailable():
                return storage_error_response()
            case list() as stations:
                pass
            case unreachable_1:
                assert_never(unreachable_1)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
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
