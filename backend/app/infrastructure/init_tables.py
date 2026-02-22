import logging
import time

from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

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

    if "stations" not in existing:
        client.create_table(
            TableName="stations",
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
        logger.info("Created table: stations")

    if "daily_temperature" not in existing:
        client.create_table(
            TableName="daily_temperature",
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
        logger.info("Created table: daily_temperature")

    if "fetch_log" not in existing:
        client.create_table(
            TableName="fetch_log",
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
        logger.info("Created table: fetch_log")

    if "scrape_jobs" not in existing:
        client.create_table(
            TableName="scrape_jobs",
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
            TableName="scrape_jobs",
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "ttl",
            },
        )
        logger.info("Created table: scrape_jobs")
