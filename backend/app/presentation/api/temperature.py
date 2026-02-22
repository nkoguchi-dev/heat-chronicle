import json
import os
from datetime import datetime

import boto3
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.application.scrape_service import ScrapeService
from app.application.temperature_service import TemperatureService
from app.di.container import JobRepoDep, StationRepoDep, TempRepoDep
from app.domain.schemas import (
    FetchJobResponse,
    JobStatusResponse,
    TemperatureResponse,
)

router = APIRouter()


@router.get("/{station_id}", response_model=TemperatureResponse)
def get_temperature(
    station_id: int,
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    start_year: int = Query(default=1975),
    end_year: int = Query(default_factory=lambda: datetime.now().year),
) -> TemperatureResponse:
    try:
        service = TemperatureService(station_repo, temp_repo)
        return service.get_temperature_data(station_id, start_year, end_year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{station_id}/fetch", response_model=FetchJobResponse)
def start_fetch(
    station_id: int,
    background_tasks: BackgroundTasks,
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    job_repo: JobRepoDep,
    start_year: int = Query(default=1975),
    end_year: int = Query(default_factory=lambda: datetime.now().year),
) -> FetchJobResponse:
    service = ScrapeService(station_repo, temp_repo, job_repo)
    try:
        job = service.create_job(station_id, start_year, end_year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    job_id = job["job_id"]
    lambda_function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

    if lambda_function_name:
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType="Event",
            Payload=json.dumps({"action": "execute_scrape_job", "job_id": job_id}),
        )
    else:
        background_tasks.add_task(service.execute_job, job_id)

    return FetchJobResponse(
        job_id=job_id,
        total_months=int(job["total"]),
    )


@router.get("/{station_id}/fetch/status", response_model=JobStatusResponse)
def get_fetch_status(
    station_id: int,
    job_repo: JobRepoDep,
    job_id: str = Query(...),
) -> JobStatusResponse:
    job = job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    current_year = job.get("current_year")
    current_month = job.get("current_month")

    return JobStatusResponse(
        status=job["status"],
        completed=int(job["completed"]),
        total=int(job["total"]),
        year=int(current_year) if current_year else None,
        month=int(current_month) if current_month else None,
        new_records=[],
        total_records=int(job["total_records"]) if job.get("total_records") else None,
        message=job.get("error_message"),
    )
