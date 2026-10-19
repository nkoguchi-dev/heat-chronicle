from datetime import datetime, timezone
from typing import Any

import pytest

from app.config import Settings
from app.domain.temperature.fetch_guard import FetchUnavailable
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
    with pytest.raises(FetchUnavailable):
        b.acquire()
    # Advance without TTL deletion; the conditional write must transfer ownership.
    clock.advance(31)
    b.acquire()
    a.release()
    b.check_owner()
    with pytest.raises(FetchUnavailable):
        a.check_owner()
    b.release()
    assert a.table.name == test_settings.table_name("fetch-log")
