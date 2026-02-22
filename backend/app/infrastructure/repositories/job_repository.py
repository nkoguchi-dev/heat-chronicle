from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from boto3.dynamodb.conditions import Attr

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 3600  # 1 hour


class JobRepository:
    def __init__(self, dynamodb: DynamoDBServiceResource):
        self.table = dynamodb.Table("scrape_jobs")

    def create_job(
        self,
        job_id: str,
        station_id: int,
        total: int,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        item: dict[str, Any] = {
            "job_id": job_id,
            "station_id": station_id,
            "status": "in_progress",
            "completed": 0,
            "total": total,
            "current_year": 0,
            "current_month": 0,
            "new_records": [],
            "total_records": 0,
            "created_at": now,
            "updated_at": now,
            "ttl": int(time.time()) + JOB_TTL_SECONDS,
        }
        self.table.put_item(Item=item)
        return item

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        response = self.table.get_item(Key={"job_id": job_id})
        return response.get("Item")

    def find_active_job(self, station_id: int) -> dict[str, Any] | None:
        response = self.table.scan(
            FilterExpression=(
                Attr("station_id").eq(station_id)
                & Attr("status").eq("in_progress")
            ),
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def update_progress(
        self,
        job_id: str,
        completed: int,
        year: int,
        month: int,
        new_records: list[dict[str, Any]],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=(
                "SET completed = :completed, "
                "current_year = :year, "
                "current_month = :month, "
                "new_records = list_append(new_records, :records), "
                "total_records = total_records + :count, "
                "updated_at = :now"
            ),
            ExpressionAttributeValues={
                ":completed": completed,
                ":year": year,
                ":month": month,
                ":records": new_records,
                ":count": len(new_records),
                ":now": now,
            },
        )

    def complete_job(self, job_id: str, total_records: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=(
                "SET #s = :status, total_records = :total_records, updated_at = :now"
            ),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": "complete",
                ":total_records": total_records,
                ":now": now,
            },
        )

    def fail_job(self, job_id: str, error_message: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=(
                "SET #s = :status, error_message = :msg, updated_at = :now"
            ),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": "error",
                ":msg": error_message,
                ":now": now,
            },
        )

    def get_and_clear_records(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_job(job_id)
        if job is None:
            return None

        if job.get("new_records"):
            self.table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET new_records = :empty",
                ExpressionAttributeValues={":empty": []},
            )

        return job
