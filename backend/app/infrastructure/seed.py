import json
import logging
from pathlib import Path

from app.infrastructure.database import get_dynamodb_resource

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def seed_stations() -> None:
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table("stations")

    response = table.scan(Select="COUNT")
    if response["Count"] > 0:
        logger.info("Stations table already seeded (%d items)", response["Count"])
        return

    stations_file = DATA_DIR / "stations.json"
    with open(stations_file, encoding="utf-8") as f:
        stations = json.load(f)

    with table.batch_writer() as batch:
        for station in stations:
            batch.put_item(Item=station)

    logger.info("Seeded %d stations", len(stations))
