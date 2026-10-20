import socket
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from app.config import Settings, settings
from app.infrastructure import database
from app.infrastructure.init_tables import ensure_tables_exist


def test_production_endpoint_remains_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    assert Settings().dynamodb_endpoint_url is None


@pytest.mark.parametrize(
    "endpoint", [None, "http://127.0.0.1:8001", "http://dynamodb-local:8000"]
)
def test_database_factories_limit_dummy_credentials_to_explicit_endpoints(
    endpoint: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "dynamodb_endpoint_url", endpoint)
    with (
        patch.object(boto3, "client") as client,
        patch.object(boto3, "resource") as resource,
    ):
        database.get_dynamodb_client()
        database.get_dynamodb_resource()
    for factory in [client, resource]:
        arguments = factory.call_args.kwargs
        if endpoint:
            assert arguments["endpoint_url"] == endpoint
            assert arguments["aws_access_key_id"] == "dummy"
            assert arguments["aws_secret_access_key"] == "dummy"
        else:
            assert "endpoint_url" not in arguments
            assert "aws_access_key_id" not in arguments
            assert "aws_secret_access_key" not in arguments


def test_unit_network_is_blocked() -> None:
    with (
        socket.socket() as connection,
        pytest.raises(AssertionError, match="must not open network"),
    ):
        connection.connect(("127.0.0.1", 8001))


@mock_aws
def test_table_initialization_is_repeatable_and_keeps_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dynamodb_endpoint_url", None)
    monkeypatch.setattr(settings, "dynamodb_table_prefix", "test-init")
    ensure_tables_exist()
    dynamodb = database.get_dynamodb_resource()
    assert set(dynamodb.meta.client.list_tables()["TableNames"]) == {
        "test-init-stations",
        "test-init-daily-temperature",
        "test-init-fetch-log",
    }
    stations = dynamodb.Table("test-init-stations")
    stations.put_item(Item={"id": 999999, "station_name": "keep-existing"})
    ensure_tables_exist()
    assert (
        stations.get_item(Key={"id": 999999})["Item"]["station_name"] == "keep-existing"
    )
    assert stations.global_secondary_indexes[0]["IndexName"] == "prec_no-index"
