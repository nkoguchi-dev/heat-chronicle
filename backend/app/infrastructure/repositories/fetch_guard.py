from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, assert_never
from uuid import uuid4

from botocore.exceptions import ClientError

from app.application.shared.ports.outbound.clock import Clock
from app.application.temperature.ports.outbound.fetch_guard import (
    GuardStorageUnavailable,
    GuardSucceeded,
    LeaseBusy,
    LeaseLost,
)
from app.config import settings
from app.infrastructure.dto.fetch_lease import FetchLeaseItemDTO
from app.infrastructure.repositories.storage_errors import (
    STORAGE_EXCEPTIONS,
    expected_storage_failure,
)

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

    def acquire(self) -> GuardSucceeded | LeaseBusy | GuardStorageUnavailable:
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
        except STORAGE_EXCEPTIONS as exc:
            if (
                isinstance(exc, ClientError)
                and exc.response["Error"]["Code"] == "ConditionalCheckFailedException"
            ):
                return LeaseBusy()
            if expected_storage_failure(exc, "lease.acquire"):
                return GuardStorageUnavailable()
            raise
        return GuardSucceeded()

    def check_owner(self) -> GuardSucceeded | LeaseLost | GuardStorageUnavailable:
        match self._read_lease():
            case LeaseLost() as lost:
                return lost
            case GuardStorageUnavailable() as failure:
                return failure
            case FetchLeaseItemDTO() as item:
                if item.owner_token != self.token or item.expires_at <= Decimal(
                    str(self.clock.now().timestamp())
                ):
                    return LeaseLost()
                return GuardSucceeded()
            case unreachable:
                assert_never(unreachable)

    async def before_attempt(
        self,
    ) -> GuardSucceeded | LeaseLost | GuardStorageUnavailable:
        while True:
            match self.check_owner():
                case GuardSucceeded():
                    pass
                case LeaseLost() | GuardStorageUnavailable() as failure:
                    return failure
                case unreachable_owner:
                    assert_never(unreachable_owner)
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
            except STORAGE_EXCEPTIONS as exc:
                if (
                    isinstance(exc, ClientError)
                    and exc.response["Error"]["Code"]
                    == "ConditionalCheckFailedException"
                ):
                    match self._read_lease():
                        case LeaseLost() | GuardStorageUnavailable() as failure_read:
                            return failure_read
                        case FetchLeaseItemDTO() as item:
                            if (
                                item.owner_token != self.token
                                or item.expires_at
                                <= Decimal(str(self.clock.now().timestamp()))
                            ):
                                return LeaseLost()
                            await asyncio.sleep(
                                max(0.01, float((item.next_start or now) - now))
                            )
                        case unreachable_read:
                            assert_never(unreachable_read)
                    continue
                if expected_storage_failure(exc, "lease.before_attempt"):
                    return GuardStorageUnavailable()
                raise
            # Recheck after SDK latency, before starting any upstream attempt.
            return self.check_owner()

    def release(self) -> GuardSucceeded | GuardStorageUnavailable:
        try:
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
        except STORAGE_EXCEPTIONS as exc:
            if (
                isinstance(exc, ClientError)
                and exc.response["Error"]["Code"] == "ConditionalCheckFailedException"
            ):
                return GuardSucceeded()
            if expected_storage_failure(exc, "lease.release"):
                return GuardStorageUnavailable()
            raise
        return GuardSucceeded()

    def _read_lease(self) -> FetchLeaseItemDTO | LeaseLost | GuardStorageUnavailable:
        try:
            item = self.table.get_item(Key=LEASE_KEY, ConsistentRead=True).get("Item")
        except STORAGE_EXCEPTIONS as exc:
            if expected_storage_failure(exc, "lease.read"):
                return GuardStorageUnavailable()
            raise
        if item is None:
            return LeaseLost()
        # Malformed stored data is an unexpected failure, not lease contention.
        return FetchLeaseItemDTO.model_validate(item)
