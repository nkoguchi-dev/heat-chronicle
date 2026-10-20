import os
from typing import Any, Generator
from unittest.mock import patch
from urllib.parse import urlsplit

import boto3
import pytest

from app.config import Settings
from integration_tests.fixtures.test_data import (
    cleanup_all_test_data,
    insert_test_stations,
)


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Require an explicit local target before any table cleanup or AWS client."""
    endpoint = os.environ.get("DYNAMODB_ENDPOINT_URL", "")
    prefix = os.environ.get("DYNAMODB_TABLE_PREFIX", "")
    try:
        target = urlsplit(endpoint)
        is_local = (
            target.scheme == "http"
            and target.hostname in {"localhost", "127.0.0.1", "::1"}
            and target.port is not None
            and target.username is None
            and target.password is None
            and target.path in {"", "/"}
            and not target.query
            and not target.fragment
        )
    except ValueError:
        is_local = False
    if not is_local or not (prefix == "test" or prefix.startswith("test-")):
        raise pytest.UsageError(
            "Integration tests require an explicit HTTP loopback DYNAMODB_ENDPOINT_URL "
            "with a port and DYNAMODB_TABLE_PREFIX=test or test-<unique-name>."
        )
    return Settings(
        dynamodb_endpoint_url=endpoint,
        dynamodb_table_prefix=prefix,
        cors_allow_origins="http://localhost:3000",
    )


@pytest.fixture(scope="session")
def dynamodb_resource(test_settings: Settings) -> Generator[Any, None, None]:
    """セッションスコープで DynamoDB Local への接続を確立する。"""
    resource = boto3.resource(
        "dynamodb",
        endpoint_url=test_settings.dynamodb_endpoint_url,
        region_name=test_settings.dynamodb_region,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
    )
    yield resource


@pytest.fixture(scope="session", autouse=True)
def setup_tables(
    dynamodb_resource: Any, test_settings: Settings
) -> Generator[None, None, None]:
    """テスト用テーブルを作成する。セッション終了後に削除する。"""
    prefix = test_settings.dynamodb_table_prefix
    stations_table = test_settings.table_name("stations")
    temp_table = test_settings.table_name("daily-temperature")
    log_table = test_settings.table_name("fetch-log")

    client = dynamodb_resource.meta.client

    existing = client.list_tables()["TableNames"]

    if stations_table not in existing:
        dynamodb_resource.create_table(
            TableName=stations_table,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "N"},
                {"AttributeName": "prec_no", "AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "prec_no-index",
                    "KeySchema": [{"AttributeName": "prec_no", "KeyType": "HASH"}],
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

    if temp_table not in existing:
        dynamodb_resource.create_table(
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

    if log_table not in existing:
        dynamodb_resource.create_table(
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

    yield

    # セッション終了後にテスト用テーブルを削除
    for table_name in [stations_table, temp_table, log_table]:
        try:
            dynamodb_resource.Table(table_name).delete()
        except Exception:
            pass

    _ = prefix  # 未使用変数の警告を避けるための参照


@pytest.fixture(scope="session", autouse=True)
def patch_settings(test_settings: Settings) -> Generator[None, None, None]:
    """リポジトリが参照する settings をテスト用設定にパッチする。
    DynamoDBStationRepository / DynamoDBTemperatureRepository は
    コンストラクタで settings を参照するため、
    DI ファクトリ実行前にパッチしておく必要がある。
    """
    with (
        patch("app.infrastructure.repositories.fetch_guard.settings", test_settings),
        patch(
            "app.infrastructure.repositories.station_repository.settings", test_settings
        ),
        patch(
            "app.infrastructure.repositories.temperature_repository.settings",
            test_settings,
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def clean_test_data(dynamodb_resource: Any, test_settings: Settings) -> None:
    """各テスト前にテストデータをクリーンアップし、基本 stations データを再投入する。"""
    cleanup_all_test_data(dynamodb_resource, test_settings.dynamodb_table_prefix)
    insert_test_stations(dynamodb_resource, test_settings.dynamodb_table_prefix)
