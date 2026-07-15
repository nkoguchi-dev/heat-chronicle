from __future__ import annotations

from typing import TYPE_CHECKING, Any

from boto3.dynamodb.conditions import Key

from app.config import settings
from app.domain.station import Station
from app.infrastructure.dto.dynamodb import StationItemDTO

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource


class DynamoDBStationRepository:
    def __init__(self, dynamodb: DynamoDBServiceResource):
        self.table = dynamodb.Table(settings.table_name("stations"))

    def get_all(self) -> list[Station]:
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {}
        while True:
            response = self.table.scan(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        items = [item for item in items if int(item["id"]) != 0]
        items.sort(key=lambda x: int(x["id"]))
        return [self._to_domain(item) for item in items]

    def get_by_prec_no(self, prec_no: int) -> list[Station]:
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {
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
        return [self._to_domain(item) for item in items]

    def get_by_id(self, station_id: int) -> Station | None:
        if station_id == 0:
            return None
        response = self.table.get_item(Key={"id": station_id})
        item = response.get("Item")
        return self._to_domain(item) if item else None

    def _to_domain(self, item: dict[str, Any]) -> Station:
        dto = StationItemDTO.model_validate(item)
        return Station(
            id=int(dto.id),
            station_name=dto.station_name,
            prec_no=int(dto.prec_no),
            block_no=dto.block_no,
            station_type=dto.station_type,
            latitude=float(dto.latitude) if dto.latitude is not None else None,
            longitude=float(dto.longitude) if dto.longitude is not None else None,
            earliest_year=(
                int(dto.earliest_year) if dto.earliest_year is not None else None
            ),
        )
