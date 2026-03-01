import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://www.data.jma.go.jp/stats/etrn/view"
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 3


class JmaClient:
    def __init__(self) -> None:
        self._last_request_time: float = 0.0
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": "heat-chronicle/1.0"},
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _wait_interval(self) -> None:
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        wait = settings.scrape_interval_sec - elapsed
        if wait > 0:
            await asyncio.sleep(wait)

    async def fetch_daily_page(
        self,
        prec_no: int,
        block_no: str,
        year: int,
        month: int,
        station_type: str,
    ) -> str:
        page = "daily_s1.php" if station_type == "s" else "daily_a1.php"
        url = f"{BASE_URL}/{page}"
        params: dict[str, str | int] = {
            "prec_no": prec_no,
            "block_no": block_no,
            "year": year,
            "month": month,
            "day": "",
            "view": "p1",
        }

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                await self._wait_interval()
                response = await self._client.get(url, params=params)
                self._last_request_time = asyncio.get_event_loop().time()
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                last_exc = e
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "JMA request failed (attempt %d): %s, retrying in %ds",
                    attempt + 1,
                    e,
                    wait,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"Failed to fetch JMA data after {MAX_RETRIES} retries: {last_exc}"
        )
