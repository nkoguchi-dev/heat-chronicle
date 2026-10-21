import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from app.application.temperature.ports.outbound.fetch_guard import (
    GuardSucceeded,
    LeaseLost,
)
from app.infrastructure.scraper.jma_client import (
    JmaClient,
    JmaPageFetched,
    JmaPageUnavailable,
)


async def test_each_retry_uses_shared_gate_and_no_final_sleep() -> None:
    before = AsyncMock(return_value=GuardSucceeded())
    client = JmaClient(before)
    try:
        with (
            patch.object(
                client._client, "get", side_effect=httpx.ConnectError("failed")
            ) as request,
            patch(
                "app.infrastructure.scraper.jma_client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep,
        ):
            assert isinstance(
                await client.fetch_daily_page(44, "47662", 2024, 1, "s"),
                JmaPageUnavailable,
            )
            assert request.call_count == 3
            assert before.await_count == 3
            assert [call.args[0] for call in sleep.await_args_list] == [2, 4]
    finally:
        await client.close()


async def test_total_attempt_timeout_and_successful_retry() -> None:
    before = AsyncMock(return_value=GuardSucceeded())
    client = JmaClient(before)
    calls = 0

    async def get(*args: object, **kwargs: object) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(0.03)
        return httpx.Response(
            200, text="ok", request=httpx.Request("GET", "https://example.com")
        )

    # Keep real sleep within the stub, while skipping only the backoff.
    real_sleep = asyncio.sleep

    async def fast_backoff(seconds: float) -> None:
        if seconds < 1:
            await real_sleep(seconds)

    try:
        with (
            patch(
                "app.infrastructure.scraper.jma_client.REQUEST_TIMEOUT_SECONDS", 0.01
            ),
            patch.object(client._client, "get", side_effect=get),
            patch(
                "app.infrastructure.scraper.jma_client.asyncio.sleep",
                side_effect=fast_backoff,
            ),
        ):
            assert await client.fetch_daily_page(
                44, "47662", 2024, 1, "s"
            ) == JmaPageFetched("ok")
            assert calls == 2
            assert before.await_count == 2
    finally:
        await client.close()


async def test_lost_lease_prevents_request() -> None:
    client = JmaClient(AsyncMock(return_value=LeaseLost()))
    try:
        with patch.object(client._client, "get", new_callable=AsyncMock) as request:
            assert isinstance(
                await client.fetch_daily_page(44, "47662", 2024, 1, "s"),
                JmaPageUnavailable,
            )
            request.assert_not_called()
    finally:
        await client.close()
