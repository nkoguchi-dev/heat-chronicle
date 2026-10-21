import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import assert_never

import httpx

from app.application.temperature.ports.outbound.fetch_guard import (
    GuardStorageUnavailable,
    GuardSucceeded,
    LeaseLost,
)
from app.domain.station.model import StationType
from app.infrastructure.dto.jma import JmaDailyPageRequestDTO

logger = logging.getLogger(__name__)

BASE_URL = "https://www.data.jma.go.jp/stats/etrn/view"
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_RETRIES = 3


@dataclass(frozen=True)
class JmaPageFetched:
    html: str


@dataclass(frozen=True)
class JmaPageUnavailable:
    pass


@dataclass(frozen=True)
class JmaPageStorageUnavailable:
    pass


class JmaClient:
    def __init__(
        self,
        before_attempt: Callable[
            [], Awaitable[GuardSucceeded | LeaseLost | GuardStorageUnavailable]
        ],
    ) -> None:
        self.before_attempt = before_attempt
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": "heat-chronicle/1.0"},
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_daily_page(
        self,
        prec_no: int,
        block_no: str,
        year: int,
        month: int,
        station_type: StationType,
    ) -> JmaPageFetched | JmaPageUnavailable | JmaPageStorageUnavailable:
        request = JmaDailyPageRequestDTO(
            prec_no=prec_no,
            block_no=block_no,
            year=year,
            month=month,
            station_type=station_type,
        )
        url = f"{BASE_URL}/{request.page}"

        for attempt in range(MAX_RETRIES):
            match await self.before_attempt():
                case GuardSucceeded():
                    pass
                case LeaseLost():
                    return JmaPageUnavailable()
                case GuardStorageUnavailable():
                    return JmaPageStorageUnavailable()
                case unreachable:
                    assert_never(unreachable)
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                    response = await self._client.get(
                        url, params=request.to_query_params()
                    )
                response.raise_for_status()
                return JmaPageFetched(response.text)
            except (httpx.HTTPStatusError, httpx.RequestError, TimeoutError) as exc:
                # Unsupported protocol/configuration must reach the unexpected-500 path.
                if isinstance(exc, httpx.UnsupportedProtocol):
                    raise
                logger.warning("jma_request_unavailable attempt=%d", attempt + 1)
                if attempt == MAX_RETRIES - 1:
                    break
                await asyncio.sleep(2 ** (attempt + 1))

        return JmaPageUnavailable()
