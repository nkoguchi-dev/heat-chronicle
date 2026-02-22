import logging
import time

from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

from app.config import settings
from app.infrastructure.database import get_dynamodb_client

logger = logging.getLogger(__name__)


def _wait_for_dynamodb(
    client, max_retries: int = 15, interval: float = 2.0
) -> list[str]:
    for attempt in range(1, max_retries + 1):
        try:
            return client.list_tables()["TableNames"]
        except (EndpointConnectionError, ClientError, ConnectionError, ReadTimeoutError) as e:
            if attempt == max_retries:
                raise
            logger.warning(
                "DynamoDB not ready (attempt %d/%d): %s",
                attempt,
                max_retries,
                e,
            )
            time.sleep(interval)
    return []  # unreachable


def ensure_tables_exist() -> None:
    client = get_dynamodb_client()
    existing = _wait_for_dynamodb(client)

    stations_table = settings.table_name("stations")
    temp_table = settings.table_name("daily-temperature")
    log_table = settings.table_name("fetch-log")
    jobs_table = settings.table_name("scrape-jobs")

    if stations_table not in existing:
        client.create_table(
            TableName=stations_table,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "N"},
                {"AttributeName": "prec_no", "AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "prec_no-index",
                    "KeySchema": [
                        {"AttributeName": "prec_no", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
        logger.info("Created table: %s", stations_table)

    if temp_table not in existing:
        client.create_table(
            TableName=temp_table,
            KeySchema=[
                {"AttributeName": "station_id", "KeyType": "HASH"},
                {"AttributeName": "date", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "station_id", "AttributeType": "N"},
                {"AttributeName": "date", "AttributeType": "S"},
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
        logger.info("Created table: %s", temp_table)

    if log_table not in existing:
        client.create_table(
            TableName=log_table,
            KeySchema=[
                {"AttributeName": "station_id", "KeyType": "HASH"},
                {"AttributeName": "year_month", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "station_id", "AttributeType": "N"},
                {"AttributeName": "year_month", "AttributeType": "S"},
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
        logger.info("Created table: %s", log_table)

    if jobs_table not in existing:
        client.create_table(
            TableName=jobs_table,
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "job_id", "AttributeType": "S"},
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
        client.update_time_to_live(
            TableName=jobs_table,
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "ttl",
            },
        )
        logger.info("Created table: %s", jobs_table)
