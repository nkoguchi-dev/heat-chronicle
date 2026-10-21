from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.temperature.ports.inbound.fetch_month import (
    FetchMonthInvalidPeriod,
    FetchMonthNotFound,
    FetchMonthResult,
    FetchMonthStorageUnavailable,
    FetchMonthUnavailable,
)
from app.main import app
from app.presentation.api.shared.dependencies import get_fetch_month_port


@pytest.mark.parametrize(
    "result,status,body",
    [
        (FetchMonthResult([]), 200, {"year": 2024, "month": 1, "records": []}),
        (FetchMonthNotFound(4), 404, {"detail": "Station 4 not found"}),
        (
            FetchMonthInvalidPeriod("month outside observation range"),
            422,
            {"detail": "month outside observation range"},
        ),
        (FetchMonthStorageUnavailable(), 500, {"detail": "Internal server error"}),
        (FetchMonthUnavailable(), 503, {"detail": "Temporarily unavailable"}),
    ],
)
async def test_monthly_result_maps_to_existing_http_contract(
    result: (
        FetchMonthResult
        | FetchMonthNotFound
        | FetchMonthInvalidPeriod
        | FetchMonthStorageUnavailable
        | FetchMonthUnavailable
    ),
    status: int,
    body: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = AsyncMock()
    port.fetch_month.return_value = result
    monkeypatch.setitem(app.dependency_overrides, get_fetch_month_port, lambda: port)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/temperature/4/fetch-month?year=2024&month=1")
    assert response.status_code == status
    assert response.json() == body
    assert response.headers.get("Retry-After") == ("5" if status == 503 else None)
    port.fetch_month.assert_awaited_once_with(4, 2024, 1)


@pytest.mark.parametrize("error", [ValueError("private"), RuntimeError("private")])
async def test_monthly_unexpected_error_uses_common_500(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = AsyncMock()
    port.fetch_month.side_effect = error
    monkeypatch.setitem(app.dependency_overrides, get_fetch_month_port, lambda: port)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/temperature/4/fetch-month?year=2024&month=1")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Retry-After" not in response.headers
