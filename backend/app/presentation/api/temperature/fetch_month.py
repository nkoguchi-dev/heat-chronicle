from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict

from app.di.container import FetchMonthUseCaseDep
from app.domain.temperature.fetch_guard import FetchUnavailable
from app.domain.temperature.input_policy import InvalidTemperatureInput

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
    use_case: FetchMonthUseCaseDep,
    year: int = Query(...),
    month: int = Query(...),
) -> MonthTemperatureResponse:
    try:
        records = await use_case.fetch_month(station_id, year, month)
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
    except FetchUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Temporarily unavailable",
            headers={"Retry-After": "5"},
        )
    except InvalidTemperatureInput as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
