from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from botocore.exceptions import ClientError
from pydantic import ValidationError

from app.application.shared.ports.outbound.clock import Clock
from app.config import settings
from app.domain.temperature.fetch_guard import FetchUnavailable
from app.infrastructure.dto.fetch_lease import FetchLeaseItemDTO

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBServiceResource

LEASE_SECONDS = 30
ATTEMPT_INTERVAL_SECONDS = 2
# Station IDs are positive. This singleton shares the existing table and IAM policy.
LEASE_KEY = {"station_id": 0, "year_month": "__upstream_lease__"}


class DynamoDBFetchGuard:
    def __init__(self, dynamodb: DynamoDBServiceResource, clock: Clock) -> None:
        self.clock = clock
        self.table = dynamodb.Table(settings.table_name("fetch-log"))
        self.token = str(uuid4())

    def acquire(self) -> None:
        now = Decimal(str(self.clock.now().timestamp()))
        try:
            self.table.update_item(
                Key=LEASE_KEY,
                UpdateExpression="SET owner_token = :token, expires_at = :expires",
                ConditionExpression=(
                    "attribute_not_exists(owner_token) OR expires_at <= :now"
                ),
                ExpressionAttributeValues={
                    ":token": self.token,
                    ":expires": now + LEASE_SECONDS,
                    ":now": now,
                },
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise FetchUnavailable() from exc
            raise

    def check_owner(self) -> None:
        item = self._read_lease()
        if item.owner_token != self.token or item.expires_at <= Decimal(
            str(self.clock.now().timestamp())
        ):
            raise FetchUnavailable()

    async def before_attempt(self) -> None:
        while True:
            self.check_owner()
            now = Decimal(str(self.clock.now().timestamp()))
            try:
                self.table.update_item(
                    Key=LEASE_KEY,
                    UpdateExpression="SET next_start = :next",
                    ConditionExpression=(
                        "owner_token = :token AND expires_at > :now AND "
                        "(attribute_not_exists(next_start) OR next_start <= :now)"
                    ),
                    ExpressionAttributeValues={
                        ":token": self.token,
                        ":now": now,
                        ":next": now + ATTEMPT_INTERVAL_SECONDS,
                    },
                )
                # Recheck after I/O; an expired process must not start another attempt.
                self.check_owner()
                return
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
                self.check_owner()
                item = self._read_lease()
                await asyncio.sleep(max(0.01, float((item.next_start or now) - now)))

    def release(self) -> None:
        try:
            # Start the cooldown after completion, including the final SDK latency.
            self.table.update_item(
                Key=LEASE_KEY,
                UpdateExpression=(
                    "SET expires_at = :zero, next_start = :next REMOVE owner_token"
                ),
                ConditionExpression="owner_token = :token",
                ExpressionAttributeValues={
                    ":token": self.token,
                    ":zero": 0,
                    ":next": Decimal(str(self.clock.now().timestamp()))
                    + ATTEMPT_INTERVAL_SECONDS,
                },
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise

    def _read_lease(self) -> FetchLeaseItemDTO:
        item = self.table.get_item(Key=LEASE_KEY, ConsistentRead=True).get("Item")
        if item is None:
            raise FetchUnavailable()
        try:
            return FetchLeaseItemDTO.model_validate(item)
        except ValidationError as exc:
            raise FetchUnavailable() from exc
