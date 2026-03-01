from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, cast

from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

from app.config import settings
from app.infrastructure.database import get_dynamodb_client

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.client import DynamoDBClient
    from mypy_boto3_dynamodb.type_defs import (
        AttributeDefinitionTypeDef,
        GlobalSecondaryIndexTypeDef,
        KeySchemaElementTypeDef,
        ProvisionedThroughputTypeDef,
    )

logger = logging.getLogger(__name__)

DEFAULT_READ_CAPACITY_UNITS = 5
DEFAULT_WRITE_CAPACITY_UNITS = 5


def _wait_for_dynamodb(
    client: DynamoDBClient, max_retries: int = 15, interval: float = 2.0
) -> list[str]:
    for attempt in range(1, max_retries + 1):
        try:
            return cast(list[str], client.list_tables()["TableNames"])
        except (
            EndpointConnectionError,
            ClientError,
            ConnectionError,
            ReadTimeoutError,
        ) as e:
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


def _create_table_if_not_exists(
    client: DynamoDBClient,
    name: str,
    existing: list[str],
    key_schema: list[KeySchemaElementTypeDef],
    attr_defs: list[AttributeDefinitionTypeDef],
    gsi: list[GlobalSecondaryIndexTypeDef] | None = None,
) -> None:
    if name in existing:
        return
    throughput: ProvisionedThroughputTypeDef = {
        "ReadCapacityUnits": DEFAULT_READ_CAPACITY_UNITS,
        "WriteCapacityUnits": DEFAULT_WRITE_CAPACITY_UNITS,
    }
    if gsi is not None:
        client.create_table(
            TableName=name,
            KeySchema=key_schema,
            AttributeDefinitions=attr_defs,
            GlobalSecondaryIndexes=gsi,
            ProvisionedThroughput=throughput,
        )
    else:
        client.create_table(
            TableName=name,
            KeySchema=key_schema,
            AttributeDefinitions=attr_defs,
            ProvisionedThroughput=throughput,
        )
    logger.info("Created table: %s", name)


def ensure_tables_exist() -> None:
    client = get_dynamodb_client()
    existing = _wait_for_dynamodb(client)

    _create_table_if_not_exists(
        client,
        settings.table_name("stations"),
        existing,
        key_schema=[{"AttributeName": "id", "KeyType": "HASH"}],
        attr_defs=[
            {"AttributeName": "id", "AttributeType": "N"},
            {"AttributeName": "prec_no", "AttributeType": "N"},
        ],
        gsi=[
            {
                "IndexName": "prec_no-index",
                "KeySchema": [{"AttributeName": "prec_no", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": DEFAULT_READ_CAPACITY_UNITS,
                    "WriteCapacityUnits": DEFAULT_WRITE_CAPACITY_UNITS,
                },
            }
        ],
    )
    _create_table_if_not_exists(
        client,
        settings.table_name("daily-temperature"),
        existing,
        key_schema=[
            {"AttributeName": "station_id", "KeyType": "HASH"},
            {"AttributeName": "date", "KeyType": "RANGE"},
        ],
        attr_defs=[
            {"AttributeName": "station_id", "AttributeType": "N"},
            {"AttributeName": "date", "AttributeType": "S"},
        ],
    )
    _create_table_if_not_exists(
        client,
        settings.table_name("fetch-log"),
        existing,
        key_schema=[
            {"AttributeName": "station_id", "KeyType": "HASH"},
            {"AttributeName": "year_month", "KeyType": "RANGE"},
        ],
        attr_defs=[
            {"AttributeName": "station_id", "AttributeType": "N"},
            {"AttributeName": "year_month", "AttributeType": "S"},
        ],
    )
