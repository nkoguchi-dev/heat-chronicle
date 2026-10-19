from typing import Any
from unittest.mock import patch

import pytest

from app.config import Settings
from app.domain.temperature.fetch_guard import FetchUnavailable
from app.infrastructure.repositories.fetch_guard import DynamoDBFetchGuard


async def test_shared_gate_on_dynamodb_local(
    dynamodb_resource: Any, test_settings: Settings
) -> None:
    # Independent repository instances represent separate Lambda executions.
    a = DynamoDBFetchGuard(dynamodb_resource)
    b = DynamoDBFetchGuard(dynamodb_resource)
    with patch(
        "app.infrastructure.repositories.fetch_guard.time.time", return_value=100
    ):
        a.acquire()
        await a.before_attempt()
        with pytest.raises(FetchUnavailable):
            b.acquire()
    # Advance without TTL deletion; the conditional write must transfer ownership.
    with patch(
        "app.infrastructure.repositories.fetch_guard.time.time", return_value=131
    ):
        b.acquire()
        a.release()
        b.check_owner()
        with pytest.raises(FetchUnavailable):
            a.check_owner()
        b.release()
    assert a.table.name == test_settings.table_name("fetch-log")
