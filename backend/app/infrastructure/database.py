from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
    kwargs: dict[str, Any] = {
        "region_name": settings.dynamodb_region,
        "config": _dynamo_config,
    }

    if settings.dynamodb_endpoint_url:
        kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
        kwargs["aws_access_key_id"] = "dummy"
        kwargs["aws_secret_access_key"] = "dummy"

    return boto3.resource("dynamodb", **kwargs)


def get_dynamodb_client() -> DynamoDBClient:
    kwargs: dict[str, Any] = {
        "region_name": settings.dynamodb_region,
        "config": _dynamo_config,
    }

    if settings.dynamodb_endpoint_url:
        kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
        kwargs["aws_access_key_id"] = "dummy"
        kwargs["aws_secret_access_key"] = "dummy"

    return boto3.client("dynamodb", **kwargs)
