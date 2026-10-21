from typing import Annotated

from fastapi import Depends, FastAPI

from app.application.prefecture.list_prefecture_use_case import ListPrefectureUseCase
from app.application.prefecture.ports.inbound.list_prefecture import ListPrefecturePort
from app.application.shared.ports.outbound.clock import Clock
from app.application.station.list_station_use_case import ListStationUseCase
from app.application.station.ports.inbound.list_station import ListStationPort
from app.application.station.ports.outbound.repository import StationRepository
from app.application.temperature.fetch_month_use_case import FetchMonthUseCase
from app.application.temperature.get_temperature_use_case import GetTemperatureUseCase
from app.application.temperature.ports.inbound.get_temperature import GetTemperaturePort
from app.application.temperature.ports.outbound.repository import TemperatureRepository
from app.domain.temperature.data_source import TemperatureDataSource
from app.domain.temperature.fetch_guard import FetchGuard
from app.infrastructure.database import get_dynamodb_resource
from app.infrastructure.repositories.fetch_guard import DynamoDBFetchGuard
from app.infrastructure.repositories.station_repository import DynamoDBStationRepository
from app.infrastructure.repositories.temperature_repository import (
    DynamoDBTemperatureRepository,
)
from app.infrastructure.scraper.jma_temperature_data_source import (
    JmaTemperatureDataSource,
)
from app.infrastructure.time.system_clock import SystemClock
from app.presentation.api.shared.dependencies import (
    get_prefecture_port,
    get_station_port,
    get_temperature_port,
)


def get_clock() -> Clock:
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]


def get_station_repository() -> StationRepository:
    return DynamoDBStationRepository(get_dynamodb_resource())


def get_temperature_repository(clock: ClockDep) -> TemperatureRepository:
    return DynamoDBTemperatureRepository(get_dynamodb_resource(), clock)


def get_fetch_guard(clock: ClockDep) -> FetchGuard:
    return DynamoDBFetchGuard(get_dynamodb_resource(), clock)


FetchGuardDep = Annotated[FetchGuard, Depends(get_fetch_guard)]


def get_temperature_data_source(guard: FetchGuardDep) -> TemperatureDataSource:
    return JmaTemperatureDataSource(guard)


StationRepoDep = Annotated[StationRepository, Depends(get_station_repository)]
TempRepoDep = Annotated[TemperatureRepository, Depends(get_temperature_repository)]
TemperatureDataSourceDep = Annotated[
    TemperatureDataSource, Depends(get_temperature_data_source)
]


def get_prefecture_use_case() -> ListPrefecturePort:
    return ListPrefectureUseCase()


def get_temperature_use_case(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    clock: ClockDep,
) -> GetTemperaturePort:
    return GetTemperatureUseCase(station_repo, temp_repo, clock)


def get_station_use_case(station_repo: StationRepoDep) -> ListStationPort:
    return ListStationUseCase(station_repo)


def get_fetch_month_use_case(
    station_repo: StationRepoDep,
    temp_repo: TempRepoDep,
    temperature_data_source: TemperatureDataSourceDep,
    guard: FetchGuardDep,
    clock: ClockDep,
) -> FetchMonthUseCase:
    return FetchMonthUseCase(
        station_repo, temp_repo, temperature_data_source, guard, clock
    )


FetchMonthUseCaseDep = Annotated[FetchMonthUseCase, Depends(get_fetch_month_use_case)]


def register_dependencies(app: FastAPI) -> None:
    """Connect migrated Inbound Ports without exposing concrete types to routes."""
    app.dependency_overrides[get_prefecture_port] = get_prefecture_use_case
    app.dependency_overrides[get_station_port] = get_station_use_case
    app.dependency_overrides[get_temperature_port] = get_temperature_use_case
