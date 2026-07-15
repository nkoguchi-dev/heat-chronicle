from typing import Annotated

from fastapi import Depends

from app.application.prefecture.get_prefecture_use_case import GetPrefectureUseCase
from app.application.station.get_station_use_case import GetStationUseCase
from app.application.temperature.scrape_service import ScrapeService
from app.application.temperature.service import TemperatureService
from app.domain.station.repository import StationRepository
from app.domain.temperature.data_source import TemperatureDataSource
from app.domain.temperature.repository import TemperatureRepository
from app.infrastructure.database import get_dynamodb_resource
from app.infrastructure.repositories.station_repository import DynamoDBStationRepository
from app.infrastructure.repositories.temperature_repository import (
    DynamoDBTemperatureRepository,
)
from app.infrastructure.scraper.jma_temperature_data_source import (
    JmaTemperatureDataSource,
)


def get_station_repository() -> StationRepository:
    return DynamoDBStationRepository(get_dynamodb_resource())


def get_temperature_repository() -> TemperatureRepository:
    return DynamoDBTemperatureRepository(get_dynamodb_resource())


def get_temperature_data_source() -> TemperatureDataSource:
    return JmaTemperatureDataSource()


StationRepoDep = Annotated[StationRepository, Depends(get_station_repository)]
TempRepoDep = Annotated[TemperatureRepository, Depends(get_temperature_repository)]
TemperatureDataSourceDep = Annotated[
    TemperatureDataSource, Depends(get_temperature_data_source)
]


def get_prefecture_use_case() -> GetPrefectureUseCase:
    return GetPrefectureUseCase()


def get_temperature_service(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
) -> TemperatureService:
    return TemperatureService(station_repo, temp_repo)


def get_station_use_case(station_repo: StationRepoDep) -> GetStationUseCase:
    return GetStationUseCase(station_repo)


def get_scrape_service(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    temperature_data_source: TemperatureDataSourceDep,
) -> ScrapeService:
    return ScrapeService(station_repo, temp_repo, temperature_data_source)


GetPrefectureUseCaseDep = Annotated[
    GetPrefectureUseCase, Depends(get_prefecture_use_case)
]
GetStationUseCaseDep = Annotated[GetStationUseCase, Depends(get_station_use_case)]
TemperatureServiceDep = Annotated[TemperatureService, Depends(get_temperature_service)]
ScrapeServiceDep = Annotated[ScrapeService, Depends(get_scrape_service)]
