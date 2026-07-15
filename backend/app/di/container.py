from typing import Annotated

from fastapi import Depends

from app.application.prefecture.list_prefecture_use_case import ListPrefectureUseCase
from app.application.station.list_station_use_case import ListStationUseCase
from app.application.temperature.fetch_month_use_case import FetchMonthUseCase
from app.application.temperature.get_temperature_use_case import GetTemperatureUseCase
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


def get_prefecture_use_case() -> ListPrefectureUseCase:
    return ListPrefectureUseCase()


def get_temperature_use_case(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
) -> GetTemperatureUseCase:
    return GetTemperatureUseCase(station_repo, temp_repo)


def get_station_use_case(station_repo: StationRepoDep) -> ListStationUseCase:
    return ListStationUseCase(station_repo)


def get_fetch_month_use_case(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    temperature_data_source: TemperatureDataSourceDep,
) -> FetchMonthUseCase:
    return FetchMonthUseCase(station_repo, temp_repo, temperature_data_source)


ListPrefectureUseCaseDep = Annotated[
    ListPrefectureUseCase, Depends(get_prefecture_use_case)
]
ListStationUseCaseDep = Annotated[ListStationUseCase, Depends(get_station_use_case)]
GetTemperatureUseCaseDep = Annotated[
    GetTemperatureUseCase, Depends(get_temperature_use_case)
]
FetchMonthUseCaseDep = Annotated[FetchMonthUseCase, Depends(get_fetch_month_use_case)]
