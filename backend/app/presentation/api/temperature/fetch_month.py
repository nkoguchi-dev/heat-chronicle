from datetime import date as Date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.di.container import ScrapeServiceDep

router = APIRouter()

MIN_MONTH = 1
MAX_MONTH = 12


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
    station_id: int,
    service: ScrapeServiceDep,
    year: int = Query(...),
    month: int = Query(...),
) -> MonthTemperatureResponse:
    if month < MIN_MONTH or month > MAX_MONTH:
        raise HTTPException(status_code=400, detail="month must be 1-12")

    try:
        records = await service.fetch_month(station_id, year, month)
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
