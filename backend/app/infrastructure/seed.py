from __future__ import annotations

import json
import logging
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from app.config import settings
from app.infrastructure.database import get_dynamodb_resource
from app.infrastructure.dto.dynamodb import (
    StationMetadataItemDTO,
    StationMetadataWriteDTO,
    StationSeedDTO,
    StationWriteDTO,
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

CURRENT_VERSION = 2


def _to_station_write_dto(station: StationSeedDTO) -> StationWriteDTO:
    return StationWriteDTO(
        id=station.id,
        station_name=station.station_name,
        prec_no=station.prec_no,
        block_no=station.block_no,
        station_type=station.station_type,
        latitude=(
            Decimal(str(station.latitude)) if station.latitude is not None else None
        ),
        longitude=(
            Decimal(str(station.longitude)) if station.longitude is not None else None
        ),
        earliest_year=station.earliest_year,
    )


def _migrate_v1_seed(table: Table, stations: list[StationSeedDTO]) -> None:
    """空テーブルへの初期投入。"""
    with table.batch_writer() as batch:
        for station in stations:
            dto = _to_station_write_dto(station)
            batch.put_item(Item=dto.model_dump(exclude_none=True))


def _migrate_v2_add_earliest_year(table: Table, stations: list[StationSeedDTO]) -> None:
    """既存レコードに earliest_year を追加。"""
    for station in stations:
        earliest_year = station.earliest_year
        if earliest_year is None:
            continue
        table.update_item(
            Key={"id": station.id},
            UpdateExpression="SET earliest_year = :val",
            ExpressionAttributeValues={":val": earliest_year},
        )


MIGRATIONS: dict[int, Callable[[Table, list[StationSeedDTO]], None]] = {
    1: _migrate_v1_seed,
    2: _migrate_v2_add_earliest_year,
}


def seed_and_migrate() -> None:
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.table_name("stations"))

    meta = table.get_item(Key={"id": 0})
    db_version = 0
    if "Item" in meta:
        metadata_item = StationMetadataItemDTO.model_validate(meta["Item"])
        db_version = int(metadata_item.schema_version)

    if db_version >= CURRENT_VERSION:
        logger.info("Stations schema up to date (version %d)", db_version)
        return

    stations_file = DATA_DIR / "stations.json"
    with open(stations_file, encoding="utf-8") as f:
        raw_stations: Any = json.load(f)
    stations = TypeAdapter(list[StationSeedDTO]).validate_python(
        raw_stations, strict=True
    )

    for version in range(db_version + 1, CURRENT_VERSION + 1):
        logger.info("Running migration v%d...", version)
        MIGRATIONS[version](table, stations)
        logger.info("Migration v%d complete", version)

    metadata_write = StationMetadataWriteDTO(id=0, schema_version=CURRENT_VERSION)
    table.put_item(Item=metadata_write.model_dump())
    logger.info("Stations schema updated to version %d", CURRENT_VERSION)
