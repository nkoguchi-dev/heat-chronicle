from __future__ import annotations

from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

from app.config import settings
from app.domain.schemas import StationResponse

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource


class StationRepository:
    def __init__(self, dynamodb: DynamoDBServiceResource):
        self.table = dynamodb.Table(settings.table_name("stations"))

    def get_all(self) -> list[StationResponse]:
        items: list[dict] = []
        kwargs: dict = {}
        while True:
            response = self.table.scan(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        items = [item for item in items if int(item["id"]) != 0]
        items.sort(key=lambda x: int(x["id"]))
        return [self._to_schema(item) for item in items]

    def get_by_prec_no(self, prec_no: int) -> list[StationResponse]:
        items: list[dict] = []
        kwargs: dict = {
            "IndexName": "prec_no-index",
            "KeyConditionExpression": Key("prec_no").eq(prec_no),
        }
        while True:
            response = self.table.query(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        items.sort(key=lambda x: x["station_name"])
        return [self._to_schema(item) for item in items]

    def get_by_id(self, station_id: int) -> StationResponse | None:
        if station_id == 0:
            return None
        response = self.table.get_item(Key={"id": station_id})
        item = response.get("Item")
        return self._to_schema(item) if item else None

    def _to_schema(self, item: dict) -> StationResponse:
        return StationResponse(
            id=int(item["id"]),
            station_name=item["station_name"],
            prec_no=int(item["prec_no"]),
            block_no=item["block_no"],
            station_type=item["station_type"],
            latitude=float(item["latitude"]) if "latitude" in item else None,
            longitude=float(item["longitude"]) if "longitude" in item else None,
            earliest_year=int(item["earliest_year"])
            if "earliest_year" in item
            else None,
        )
