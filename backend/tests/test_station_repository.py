from typing import Any, Generator
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from app.config import Settings
from app.infrastructure.repositories.station_repository import StationRepository

TABLE_NAME = "stations"

SAMPLE_ITEMS: list[dict[str, Any]] = [
    {
        "id": 0,
        "schema_version": 2,
    },
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
    },
]

test_settings = Settings(
    dynamodb_endpoint_url=None,
    dynamodb_region="ap-northeast-1",
    dynamodb_table_prefix="",
)


@pytest.fixture()
def repo() -> Generator[StationRepository, None, None]:
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "N"},
                {"AttributeName": "prec_no", "AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "prec_no-index",
                    "KeySchema": [
                        {"AttributeName": "prec_no", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        with table.batch_writer() as batch:
            for item in SAMPLE_ITEMS:
                batch.put_item(Item=item)

        with patch(
            "app.infrastructure.repositories.station_repository.settings",
            test_settings,
        ):
            yield StationRepository(dynamodb)


class TestGetAll:
    def test_excludes_id_zero(self, repo: StationRepository) -> None:
        stations = repo.get_all()
        ids = [s.id for s in stations]
        assert 0 not in ids
        assert len(stations) == 2

    def test_sorted_by_id(self, repo: StationRepository) -> None:
        stations = repo.get_all()
        assert stations[0].id == 1
        assert stations[1].id == 2


class TestGetById:
    def test_returns_none_for_id_zero(self, repo: StationRepository) -> None:
        assert repo.get_by_id(0) is None

    def test_returns_station(self, repo: StationRepository) -> None:
        station = repo.get_by_id(1)
        assert station is not None
        assert station.id == 1
        assert station.station_name == "札幌"

    def test_returns_none_for_nonexistent(self, repo: StationRepository) -> None:
        assert repo.get_by_id(999) is None


class TestEarliestYear:
    def test_earliest_year_present(self, repo: StationRepository) -> None:
        station = repo.get_by_id(1)
        assert station is not None
        assert station.earliest_year == 1872

    def test_earliest_year_absent(self, repo: StationRepository) -> None:
        station = repo.get_by_id(2)
        assert station is not None
        assert station.earliest_year is None
