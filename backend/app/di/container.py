from typing import Annotated

from fastapi import Depends

from app.infrastructure.database import get_dynamodb_resource
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import (
    TemperatureRepository,
)


def get_station_repository() -> StationRepository:
    return StationRepository(get_dynamodb_resource())


def get_temperature_repository() -> TemperatureRepository:
    return TemperatureRepository(get_dynamodb_resource())


StationRepoDep = Annotated[StationRepository, Depends(get_station_repository)]
TempRepoDep = Annotated[TemperatureRepository, Depends(get_temperature_repository)]
