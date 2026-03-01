from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.infrastructure.database import get_dynamodb_resource

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

CURRENT_VERSION = 2


def _migrate_v1_seed(table: Table, stations: list[dict[str, object]]) -> None:
    """空テーブルへの初期投入。"""
    with table.batch_writer() as batch:
        for station in stations:
            batch.put_item(Item=station)


def _migrate_v2_add_earliest_year(
    table: Table, stations: list[dict[str, object]]
) -> None:
    """既存レコードに earliest_year を追加。"""
    for station in stations:
        earliest_year = station.get("earliest_year")
        if earliest_year is None:
            continue
        table.update_item(
            Key={"id": station["id"]},
            UpdateExpression="SET earliest_year = :val",
            ExpressionAttributeValues={":val": earliest_year},
        )


MIGRATIONS: dict[int, Callable[[Table, list[dict[str, object]]], None]] = {
    1: _migrate_v1_seed,
    2: _migrate_v2_add_earliest_year,
}


def seed_and_migrate() -> None:
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.table_name("stations"))

    meta = table.get_item(Key={"id": 0})
    db_version = 0
    if "Item" in meta:
        db_version = int(meta["Item"].get("schema_version", 0))

    if db_version >= CURRENT_VERSION:
        logger.info("Stations schema up to date (version %d)", db_version)
        return

    stations_file = DATA_DIR / "stations.json"
    with open(stations_file, encoding="utf-8") as f:
        stations = json.load(f)

    for version in range(db_version + 1, CURRENT_VERSION + 1):
        logger.info("Running migration v%d...", version)
        MIGRATIONS[version](table, stations)
        logger.info("Migration v%d complete", version)

    table.put_item(Item={"id": 0, "schema_version": CURRENT_VERSION})
    logger.info("Stations schema updated to version %d", CURRENT_VERSION)
