from datetime import datetime, timezone
from typing import Any

from app.application.temperature.ports.outbound.fetch_guard import LeaseBusy, LeaseLost
from app.config import Settings
from app.infrastructure.repositories.fetch_guard import DynamoDBFetchGuard
from tests.fixed_clock import FixedClock


async def test_shared_gate_on_dynamodb_local(
    dynamodb_resource: Any, test_settings: Settings
) -> None:
    # Independent repository instances represent separate Lambda executions.
    clock = FixedClock(datetime.fromtimestamp(100, timezone.utc))
    a = DynamoDBFetchGuard(dynamodb_resource, clock)
    b = DynamoDBFetchGuard(dynamodb_resource, clock)
    a.acquire()
    await a.before_attempt()
    assert isinstance(b.acquire(), LeaseBusy)
    # Advance without TTL deletion; the conditional write must transfer ownership.
    clock.advance(31)
    b.acquire()
    a.release()
    b.check_owner()
    assert isinstance(a.check_owner(), LeaseLost)
    b.release()
    assert a.table.name == test_settings.table_name("fetch-log")
