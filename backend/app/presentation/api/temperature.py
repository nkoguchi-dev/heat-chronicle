from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.application.scrape_service import ScrapeService
from app.application.temperature_service import TemperatureService
from app.di.container import JobRepoDep, StationRepoDep, TempRepoDep
from app.domain.schemas import (
    FetchJobResponse,
    JobStatusResponse,
    TemperatureRecord,
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

    background_tasks.add_task(service.execute_job, job["job_id"])

    return FetchJobResponse(
        job_id=job["job_id"],
        total_months=int(job["total"]),
    )


@router.get("/{station_id}/fetch/status", response_model=JobStatusResponse)
def get_fetch_status(
    station_id: int,
    job_repo: JobRepoDep,
    job_id: str = Query(...),
) -> JobStatusResponse:
    job_repo_instance = job_repo
    job = job_repo_instance.get_and_clear_records(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    new_records = [
        TemperatureRecord(
            date=r["date"],
            max_temp=float(r["max_temp"]) if r.get("max_temp") is not None else None,
            min_temp=float(r["min_temp"]) if r.get("min_temp") is not None else None,
            avg_temp=float(r["avg_temp"]) if r.get("avg_temp") is not None else None,
        )
        for r in job.get("new_records", [])
    ]

    current_year = job.get("current_year")
    current_month = job.get("current_month")

    return JobStatusResponse(
        status=job["status"],
        completed=int(job["completed"]),
        total=int(job["total"]),
        year=int(current_year) if current_year else None,
        month=int(current_month) if current_month else None,
        new_records=new_records,
        total_records=int(job["total_records"]) if job.get("total_records") else None,
        message=job.get("error_message"),
    )
