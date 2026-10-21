from datetime import date as Date
from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.application.temperature.ports.inbound.errors import InvalidTemperatureInput
from app.application.temperature.ports.inbound.get_temperature import (
    GetTemperatureDataOutput,
    GetTemperaturePort,
    GetTemperatureStorageUnavailable,
)
from app.presentation.api.shared.dependencies import get_temperature_port
from app.presentation.api.shared.internal_server_error import storage_error_response

router = APIRouter()


class TemperatureRecordResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    date: Date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


class TemperatureMetadataResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    station_id: int
    station_name: str
    start_year: int
    end_year: int
    total_records: int
    fetched_months: list[str]
    fetching_required: bool
    has_older_data: bool
    next_end_year: int | None


class TemperatureResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    metadata: TemperatureMetadataResponse
    data: list[TemperatureRecordResponse]


@router.get("/{station_id}", response_model=TemperatureResponse)
def get_temperature(
    station_id: Annotated[int, Path(gt=0)],
    use_case: Annotated[GetTemperaturePort, Depends(get_temperature_port)],
    end_year: int | None = Query(default=None),
) -> TemperatureResponse | JSONResponse:
    try:
        match use_case.get_temperature_data(station_id, end_year):
            case GetTemperatureStorageUnavailable():
                return storage_error_response()
            case GetTemperatureDataOutput() as output:
                pass
            case unreachable_1:
                assert_never(unreachable_1)
        metadata = output.metadata
        return TemperatureResponse(
            metadata=TemperatureMetadataResponse(
                station_id=metadata.station_id,
                station_name=metadata.station_name,
                start_year=metadata.start_year,
                end_year=metadata.end_year,
                total_records=metadata.total_records,
                fetched_months=metadata.fetched_months,
                fetching_required=metadata.fetching_required,
                has_older_data=metadata.has_older_data,
                next_end_year=metadata.next_end_year,
            ),
            data=[
                TemperatureRecordResponse(
                    date=record.date,
                    max_temp=record.max_temp,
                    min_temp=record.min_temp,
                    avg_temp=record.avg_temp,
                )
                for record in output.data
            ],
        )
    except InvalidTemperatureInput as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
