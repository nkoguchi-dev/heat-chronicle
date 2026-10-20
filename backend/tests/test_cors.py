"""Exercise the real ASGI CORS boundary without AWS or lifespan side effects."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

ORIGIN = settings.cors_allow_origins.split(",")[0]
ALLOWED_HEADERS = {"accept", "accept-language", "content-language", "content-type"}


def comma_set(value: str) -> set[str]:
    return {part.strip().lower() for part in value.split(",")}


async def test_get_preflight_supports_the_frontend_without_credentials() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert comma_set(response.headers["Access-Control-Allow-Methods"]) == {"get"}
    assert (
        comma_set(response.headers["Access-Control-Allow-Headers"]) == ALLOWED_HEADERS
    )
    assert response.headers["Access-Control-Max-Age"] == "86400"
    assert "Access-Control-Allow-Credentials" not in response.headers


@pytest.mark.parametrize(
    "origin,method,header",
    [
        ("https://example.invalid", "GET", "content-type"),
        ("null", "GET", "content-type"),
        (ORIGIN, "POST", "content-type"),
        (ORIGIN, "PUT", "content-type"),
        (ORIGIN, "DELETE", "content-type"),
        (ORIGIN, "HEAD", "content-type"),
        (ORIGIN, "GET", "authorization"),
        (ORIGIN, "GET", "x-custom-header"),
    ],
)
async def test_preflight_rejects_outside_the_contract(
    origin: str, method: str, header: str
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": header,
            },
        )
    assert response.status_code == 400
    assert "Access-Control-Allow-Credentials" not in response.headers
    if origin != ORIGIN:
        assert "Access-Control-Allow-Origin" not in response.headers
    assert comma_set(response.headers["Access-Control-Allow-Methods"]) == {"get"}
    assert "authorization" not in comma_set(
        response.headers["Access-Control-Allow-Headers"]
    )


@pytest.mark.parametrize("origin", [ORIGIN, "https://example.invalid"])
async def test_actual_get_exposes_retry_guidance_only_to_allowed_origin(
    origin: str,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200  # CORS is not server-side authentication.
    assert "Access-Control-Allow-Credentials" not in response.headers
    assert comma_set(response.headers["Access-Control-Expose-Headers"]) == {
        "retry-after"
    }
    assert response.headers.get("Access-Control-Allow-Origin") == (
        ORIGIN if origin == ORIGIN else None
    )


def test_public_openapi_methods_remain_within_the_get_contract() -> None:
    for operations in app.openapi()["paths"].values():
        assert set(operations) == {"get"}
