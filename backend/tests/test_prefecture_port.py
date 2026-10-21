import json
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mangum.types import LambdaContext

from app.application.prefecture.ports.inbound.list_prefecture import (
    ListPrefecturePort,
    PrefectureOutput,
)
from app.di.container import register_dependencies
from app.presentation.api.prefectures.get_prefectures import router
from app.presentation.api.shared.dependencies import get_prefecture_port


class FakePrefecturePort:
    def __init__(self, output: list[PrefectureOutput]) -> None:
        self.output = output

    def list_prefectures(self) -> list[PrefectureOutput]:
        return self.output


def routed_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/prefectures")
    return app


@pytest.mark.parametrize(
    "output",
    [
        [],
        [PrefectureOutput(prec_no=44, name="東京都"), PrefectureOutput(14, "石狩地方")],
    ],
)
async def test_endpoint_uses_port_override_and_converts_output(
    output: list[PrefectureOutput],
) -> None:
    app = routed_app()
    register_dependencies(app)

    def fake_provider() -> ListPrefecturePort:
        return FakePrefecturePort(output)

    app.dependency_overrides[get_prefecture_port] = fake_provider
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prefectures/")
    assert response.status_code == 200
    assert response.json() == [
        {"prec_no": item.prec_no, "name": item.name} for item in output
    ]


async def test_composition_root_registers_real_provider() -> None:
    app = routed_app()
    register_dependencies(app)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prefectures/")
    assert response.status_code == 200
    assert len(response.json()) == 61
    assert {"prec_no": 44, "name": "東京都"} in response.json()


async def test_missing_provider_fails_explicitly() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=routed_app()), base_url="http://test"
    ) as client:
        with pytest.raises(
            RuntimeError, match="ListPrefecturePort provider is not registered"
        ):
            await client.get("/api/prefectures/")


def test_lambda_import_registers_prefecture_port_without_lifespan() -> None:
    # Lambda uses lifespan=off, so wiring must happen at app construction.
    with patch("app.di.lifecycle.seed_and_migrate"):
        from app.handler import handler

    response = handler(
        {
            "version": "2.0",
            "routeKey": "GET /api/prefectures/",
            "rawPath": "/api/prefectures/",
            "rawQueryString": "",
            "headers": {},
            "isBase64Encoded": False,
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/api/prefectures/",
                    "sourceIp": "127.0.0.1",
                    "protocol": "HTTP/1.1",
                },
                "requestId": "prefecture-port-test",
                "stage": "$default",
            },
        },
        cast(LambdaContext, None),
    )
    assert response["statusCode"] == 200
    body = json.loads(str(response["body"]))
    assert len(body) == 61
    assert {"prec_no": 44, "name": "東京都"} in body
