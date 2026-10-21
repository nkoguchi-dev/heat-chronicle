from datetime import date as Date
from typing import Annotated, assert_never

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.application.temperature.ports.inbound.fetch_month import (
    FetchMonthInvalidPeriod,
    FetchMonthNotFound,
    FetchMonthPort,
    FetchMonthResult,
    FetchMonthStorageUnavailable,
    FetchMonthUnavailable,
)
from app.presentation.api.shared.dependencies import get_fetch_month_port
from app.presentation.api.shared.internal_server_error import storage_error_response

router = APIRouter()


class MonthTemperatureRecordResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    date: Date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None


class MonthTemperatureResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    year: int
    month: int
    records: list[MonthTemperatureRecordResponse]


@router.get("/{station_id}/fetch-month", response_model=MonthTemperatureResponse)
async def fetch_month(
    station_id: Annotated[int, Path(gt=0)],
    use_case: Annotated[FetchMonthPort, Depends(get_fetch_month_port)],
    year: int = Query(...),
    month: int = Query(...),
) -> MonthTemperatureResponse | JSONResponse:
    match await use_case.fetch_month(station_id, year, month):
        case FetchMonthStorageUnavailable():
            return storage_error_response()
        case FetchMonthNotFound(station_id=missing_id):
            return JSONResponse(
                status_code=404, content={"detail": f"Station {missing_id} not found"}
            )
        case FetchMonthInvalidPeriod(detail=detail):
            return JSONResponse(status_code=422, content={"detail": detail})
        case FetchMonthUnavailable():
            return JSONResponse(
                status_code=503,
                content={"detail": "Temporarily unavailable"},
                headers={"Retry-After": "5"},
            )
        case FetchMonthResult(records=records):
            return MonthTemperatureResponse(
                year=year,
                month=month,
                records=[
                    MonthTemperatureRecordResponse(
                        date=record.date,
                        max_temp=record.max_temp,
                        min_temp=record.min_temp,
                        avg_temp=record.avg_temp,
                    )
                    for record in records
                ],
            )
        case unreachable:
            assert_never(unreachable)
