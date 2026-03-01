from typing import Any, Generator
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from app.config import Settings
from app.infrastructure.seed import CURRENT_VERSION, seed_and_migrate

TABLE_NAME = "stations"

SAMPLE_STATIONS = [
    {
        "id": 1,
        "station_name": "札幌",
        "prec_no": 14,
        "block_no": "47412",
        "station_type": "s",
        "earliest_year": 1872,
    },
    {
        "id": 2,
        "station_name": "仙台",
        "prec_no": 34,
        "block_no": "47590",
        "station_type": "s",
        "earliest_year": 1872,
    },
]

test_settings = Settings(
    dynamodb_endpoint_url=None,
    dynamodb_region="ap-northeast-1",
    dynamodb_table_prefix="",
)


@pytest.fixture()
def dynamodb_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield table


def _run_seed_with_patches() -> None:
    with (
        patch("app.infrastructure.seed.settings", test_settings),
        patch(
            "app.infrastructure.seed.get_dynamodb_resource",
            return_value=boto3.resource("dynamodb", region_name="ap-northeast-1"),
        ),
        patch("builtins.open", create=True) as mock_open,
        patch("json.load", return_value=SAMPLE_STATIONS),
    ):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: None
        seed_and_migrate()


class TestSeedAndMigrate:
    def test_empty_table_runs_all_migrations(self, dynamodb_table: Any) -> None:
        """空テーブル → v1, v2 が実行される。"""
        _run_seed_with_patches()

        meta = dynamodb_table.get_item(Key={"id": 0})
        assert "Item" in meta
        assert int(meta["Item"]["schema_version"]) == CURRENT_VERSION

        response = dynamodb_table.scan()
        items = [item for item in response["Items"] if int(item["id"]) != 0]
        assert len(items) == len(SAMPLE_STATIONS)

        for item in items:
            assert "earliest_year" in item

    def test_v1_done_runs_only_v2(self, dynamodb_table: Any) -> None:
        """v1 済み → v2 のみ実行される。"""
        with dynamodb_table.batch_writer() as batch:
            for station in SAMPLE_STATIONS:
                item = {k: v for k, v in station.items() if k != "earliest_year"}
                batch.put_item(Item=item)
        dynamodb_table.put_item(Item={"id": 0, "schema_version": 1})

        _run_seed_with_patches()

        meta = dynamodb_table.get_item(Key={"id": 0})
        assert int(meta["Item"]["schema_version"]) == CURRENT_VERSION

        item = dynamodb_table.get_item(Key={"id": 1})["Item"]
        assert int(item["earliest_year"]) == 1872

    def test_v2_done_skips(self, dynamodb_table: Any) -> None:
        """v2 済み → 即リターン。"""
        dynamodb_table.put_item(Item={"id": 0, "schema_version": CURRENT_VERSION})

        with (
            patch("app.infrastructure.seed.settings", test_settings),
            patch(
                "app.infrastructure.seed.get_dynamodb_resource",
                return_value=boto3.resource("dynamodb", region_name="ap-northeast-1"),
            ),
        ):
            seed_and_migrate()

        response = dynamodb_table.scan()
        assert response["Count"] == 1
