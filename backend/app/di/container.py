from typing import Annotated

from fastapi import Depends

from app.application.prefecture_service import PrefectureService
from app.application.scrape_service import ScrapeService
from app.application.temperature_service import TemperatureService
from app.infrastructure.database import get_dynamodb_resource
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import TemperatureRepository


def get_station_repository() -> StationRepository:
    return StationRepository(get_dynamodb_resource())


def get_temperature_repository() -> TemperatureRepository:
    return TemperatureRepository(get_dynamodb_resource())


StationRepoDep = Annotated[StationRepository, Depends(get_station_repository)]
TempRepoDep = Annotated[TemperatureRepository, Depends(get_temperature_repository)]


def get_prefecture_service() -> PrefectureService:
    return PrefectureService()


def get_temperature_service(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
) -> TemperatureService:
    return TemperatureService(station_repo, temp_repo)


def get_scrape_service(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
) -> ScrapeService:
    return ScrapeService(station_repo, temp_repo)


PrefectureServiceDep = Annotated[PrefectureService, Depends(get_prefecture_service)]
TemperatureServiceDep = Annotated[TemperatureService, Depends(get_temperature_service)]
ScrapeServiceDep = Annotated[ScrapeService, Depends(get_scrape_service)]
