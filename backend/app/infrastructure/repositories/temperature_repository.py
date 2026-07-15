from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from boto3.dynamodb.conditions import Key

from app.config import settings
from app.domain.temperature.model import DailyTemperature
from app.infrastructure.dto.dynamodb import (
    DailyTemperatureItemDTO,
    DailyTemperatureWriteDTO,
    FetchLogItemDTO,
    FetchLogWriteDTO,
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource


class DynamoDBTemperatureRepository:
    def __init__(self, dynamodb: DynamoDBServiceResource):
        self.temp_table = dynamodb.Table(settings.table_name("daily-temperature"))
        self.log_table = dynamodb.Table(settings.table_name("fetch-log"))

    def get_by_station_and_range(
        self, station_id: int, start_date: str, end_date: str
    ) -> list[DailyTemperature]:
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {
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
        return [self._to_domain(item) for item in items]

    def get_fetched_months(self, station_id: int) -> dict[tuple[int, int], datetime]:
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("station_id").eq(station_id),
        }
        while True:
            response = self.log_table.query(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        results: dict[tuple[int, int], datetime] = {}
        for item in items:
            dto = FetchLogItemDTO.model_validate(item)
            year, month = dto.year_month.split("-")
            fetched_at = datetime.fromisoformat(dto.fetched_at)
            results[(int(year), int(month))] = fetched_at
        return results

    def bulk_insert_temperatures(
        self, station_id: int, records: list[DailyTemperature]
    ) -> None:
        if not records:
            return
        with self.temp_table.batch_writer() as batch:
            for record in records:
                dto = DailyTemperatureWriteDTO(
                    station_id=station_id,
                    date=record.date.isoformat(),
                    max_temp=(
                        Decimal(str(record.max_temp))
                        if record.max_temp is not None
                        else None
                    ),
                    min_temp=(
                        Decimal(str(record.min_temp))
                        if record.min_temp is not None
                        else None
                    ),
                    avg_temp=(
                        Decimal(str(record.avg_temp))
                        if record.avg_temp is not None
                        else None
                    ),
                )
                batch.put_item(Item=dto.model_dump(exclude_none=True))

    def insert_fetch_log(self, station_id: int, year: int, month: int) -> None:
        dto = FetchLogWriteDTO(
            station_id=station_id,
            year_month=f"{year:04d}-{month:02d}",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        self.log_table.put_item(Item=dto.model_dump())

    def _to_domain(self, item: dict[str, Any]) -> DailyTemperature:
        dto = DailyTemperatureItemDTO.model_validate(item)
        return DailyTemperature(
            date=datetime.strptime(dto.date, "%Y-%m-%d").date(),
            max_temp=float(dto.max_temp) if dto.max_temp is not None else None,
            min_temp=float(dto.min_temp) if dto.min_temp is not None else None,
            avg_temp=float(dto.avg_temp) if dto.avg_temp is not None else None,
        )
