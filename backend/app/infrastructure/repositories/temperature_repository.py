from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

from app.config import settings
from app.domain.schemas import TemperatureRecord

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource


class TemperatureRepository:
    def __init__(self, dynamodb: DynamoDBServiceResource):
        self.temp_table = dynamodb.Table(settings.table_name("daily-temperature"))
        self.log_table = dynamodb.Table(settings.table_name("fetch-log"))

    def get_by_station_and_range(
        self, station_id: int, start_date: str, end_date: str
    ) -> list[TemperatureRecord]:
        items: list[dict] = []
        kwargs: dict = {
            "KeyConditionExpression": (
                Key("station_id").eq(station_id)
                & Key("date").between(start_date, end_date)
            ),
        }
        while True:
            response = self.temp_table.query(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return [self._to_record(item) for item in items]

    def get_fetched_months(self, station_id: int) -> list[tuple[int, int]]:
        items: list[dict] = []
        kwargs: dict = {
            "KeyConditionExpression": Key("station_id").eq(station_id),
        }
        while True:
            response = self.log_table.query(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        results = []
        for item in items:
            year, month = item["year_month"].split("-")
            results.append((int(year), int(month)))
        return results

    def bulk_insert_temperatures(self, records: list[dict]) -> None:
        if not records:
            return
        with self.temp_table.batch_writer() as batch:
            for record in records:
                item: dict = {
                    "station_id": record["station_id"],
                    "date": record["date"],
                }
                if record.get("max_temp") is not None:
                    item["max_temp"] = Decimal(str(record["max_temp"]))
                if record.get("min_temp") is not None:
                    item["min_temp"] = Decimal(str(record["min_temp"]))
                if record.get("avg_temp") is not None:
                    item["avg_temp"] = Decimal(str(record["avg_temp"]))
                batch.put_item(Item=item)

    def insert_fetch_log(self, station_id: int, year: int, month: int) -> None:
        self.log_table.put_item(
            Item={
                "station_id": station_id,
                "year_month": f"{year:04d}-{month:02d}",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _to_record(self, item: dict) -> TemperatureRecord:
        return TemperatureRecord(
            date=item["date"],
            max_temp=float(item["max_temp"]) if "max_temp" in item else None,
            min_temp=float(item["min_temp"]) if "min_temp" in item else None,
            avg_temp=float(item["avg_temp"]) if "avg_temp" in item else None,
        )
