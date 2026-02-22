from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from app.config import settings

_dynamo_config = Config(
    connect_timeout=5,
    read_timeout=5,
    retries={"max_attempts": 0},
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource
    from mypy_boto3_dynamodb.client import DynamoDBClient


def get_dynamodb_resource() -> DynamoDBServiceResource:
    return boto3.resource(
        "dynamodb",
        endpoint_url=settings.dynamodb_endpoint_url,
        region_name=settings.dynamodb_region,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        config=_dynamo_config,
    )


def get_dynamodb_client() -> DynamoDBClient:
    return boto3.client(
        "dynamodb",
        endpoint_url=settings.dynamodb_endpoint_url,
        region_name=settings.dynamodb_region,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        config=_dynamo_config,
    )
