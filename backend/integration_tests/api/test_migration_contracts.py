"""Public API regression baseline for the Port/Adapter migration (#154)."""

from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app
from integration_tests.fixtures.mock_overrides import MockTemperatureDataSource
from integration_tests.fixtures.test_data import (
    SAMPLE_JMA_HTML,
    insert_test_temperatures,
)


@pytest.mark.asyncio
async def test_hello_contract(client: AsyncClient) -> None:
    response = await client.get("/api/hello/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


@pytest.mark.asyncio
async def test_station_exact_public_fields(client: AsyncClient) -> None:
    response = await client.get("/api/stations/", params={"prec_no": 44})
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 47662,
            "station_name": "東京",
            "prec_no": 44,
            "block_no": "47662",
            "station_type": "s",
            "latitude": 35.6917,
            "longitude": 139.75,
            "earliest_year": 1875,
        }
    ]


@pytest.mark.asyncio
async def test_temperature_exact_window_and_records(
    client: AsyncClient, dynamodb_resource: Any, test_settings: Settings
) -> None:
    insert_test_temperatures(dynamodb_resource, test_settings.dynamodb_table_prefix)
    response = await client.get("/api/temperature/47662", params={"end_year": 2024})
    assert response.status_code == 200
    assert response.json() == {
        "metadata": {
            "station_id": 47662,
            "station_name": "東京",
            "start_year": 1975,
            "end_year": 2024,
            "total_records": 3,
            "fetched_months": [],
            "fetching_required": True,
            "has_older_data": True,
            "next_end_year": 1974,
        },
        "data": [
            {
                "date": "2024-08-01",
                "max_temp": 35.2,
                "min_temp": 26.1,
                "avg_temp": 30.5,
            },
            {
                "date": "2024-08-02",
                "max_temp": 34.1,
                "min_temp": 25.8,
                "avg_temp": 29.8,
            },
            {
                "date": "2024-08-03",
                "max_temp": 36.0,
                "min_temp": 27.0,
                "avg_temp": 31.0,
            },
        ],
    }


@pytest.mark.asyncio
async def test_temperature_earliest_window_and_nulls(
    client: AsyncClient, dynamodb_resource: Any, test_settings: Settings
) -> None:
    table = dynamodb_resource.Table(test_settings.table_name("daily-temperature"))
    table.put_item(Item={"station_id": 47662, "date": "1875-01-01"})
    response = await client.get("/api/temperature/47662", params={"end_year": 1875})
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["start_year"] == 1875
    assert body["metadata"]["has_older_data"] is False
    assert body["metadata"]["next_end_year"] is None
    assert body["data"] == [
        {"date": "1875-01-01", "max_temp": None, "min_temp": None, "avg_temp": None}
    ]


@pytest.mark.asyncio
async def test_fetch_month_exact_records(
    client: AsyncClient, mock_temperature_data_source: MockTemperatureDataSource
) -> None:
    mock_temperature_data_source.set_response(2024, 8, SAMPLE_JMA_HTML)
    response = await client.get(
        "/api/temperature/47662/fetch-month", params={"year": 2024, "month": 8}
    )
    assert response.status_code == 200
    assert response.json() == {
        "year": 2024,
        "month": 8,
        "records": [
            {
                "date": "2024-08-01",
                "max_temp": 35.2,
                "min_temp": 26.1,
                "avg_temp": 30.5,
            },
            {
                "date": "2024-08-02",
                "max_temp": 34.1,
                "min_temp": 25.8,
                "avg_temp": 29.8,
            },
            {
                "date": "2024-08-03",
                "max_temp": 36.0,
                "min_temp": 27.0,
                "avg_temp": 31.0,
            },
        ],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "params", "detail"),
    [
        ("/api/stations/", {"prec_no": 99999}, "Prefecture not found"),
        ("/api/temperature/99999", {}, "Station 99999 not found"),
        (
            "/api/temperature/99999/fetch-month",
            {"year": 2024, "month": 8},
            "Station 99999 not found",
        ),
    ],
)
async def test_not_found_contract(
    client: AsyncClient, path: str, params: dict[str, int], detail: str
) -> None:
    response = await client.get(path, params=params)
    assert response.status_code == 404
    assert response.json() == {"detail": detail}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/stations/", {"prec_no": "invalid"}),
        ("/api/temperature/0", {}),
        ("/api/temperature/invalid", {}),
        ("/api/temperature/47662", {"end_year": "invalid"}),
        ("/api/temperature/47662/fetch-month", {}),
        ("/api/temperature/0/fetch-month", {"year": "2024", "month": "8"}),
        ("/api/temperature/47662/fetch-month", {"year": "2024", "month": "invalid"}),
    ],
)
async def test_http_validation_contract(
    client: AsyncClient, path: str, params: dict[str, str]
) -> None:
    response = await client.get(path, params=params)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.asyncio
@pytest.mark.parametrize("end_year", [1874, 2027])
async def test_observation_year_error_contract(
    client: AsyncClient, end_year: int
) -> None:
    response = await client.get("/api/temperature/47662", params={"end_year": end_year})
    assert response.status_code == 422
    assert response.json() == {"detail": "year outside observation range"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (RuntimeError("upstream private detail"), 500, "Internal server error"),
        (TimeoutError("upstream private detail"), 503, "Temporarily unavailable"),
        (OSError("upstream private detail"), 500, "Internal server error"),
    ],
)
async def test_upstream_failure_contract_and_no_fetch_log(
    client: AsyncClient,
    mock_temperature_data_source: MockTemperatureDataSource,
    dynamodb_resource: Any,
    test_settings: Settings,
    error: Exception,
    status: int,
    detail: str,
) -> None:
    # Keep real Use Case, DI and local repositories; fail only external I/O.
    with patch.object(
        mock_temperature_data_source, "fetch_daily_temperatures", side_effect=error
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as error_client:
            response = await error_client.get(
                "/api/temperature/47662/fetch-month", params={"year": 2024, "month": 8}
            )
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert response.headers.get("Retry-After") == ("5" if status == 503 else None)
    table = dynamodb_resource.Table(test_settings.table_name("fetch-log"))
    assert "Item" not in table.get_item(
        Key={"station_id": 47662, "year_month": "2024-08"}
    )
    # Lease release must allow a subsequent request to complete normally.
    mock_temperature_data_source.set_response(2024, 8, SAMPLE_JMA_HTML)
    retry = await client.get(
        "/api/temperature/47662/fetch-month", params={"year": 2024, "month": 8}
    )
    assert retry.status_code == 200


@pytest.mark.parametrize("storage", [False, True])
async def test_typed_upstream_failure_with_real_use_case_and_local_db(
    client: AsyncClient,
    mock_temperature_data_source: MockTemperatureDataSource,
    dynamodb_resource: Any,
    test_settings: Settings,
    storage: bool,
) -> None:
    from app.application.temperature.ports.outbound.data_source import (
        TemperatureSourceStorageUnavailable,
        TemperatureSourceUnavailable,
    )

    outcome = (
        TemperatureSourceStorageUnavailable()
        if storage
        else TemperatureSourceUnavailable()
    )
    with patch.object(
        mock_temperature_data_source, "fetch_daily_temperatures", return_value=outcome
    ):
        response = await client.get(
            "/api/temperature/47662/fetch-month",
            params={"year": 2024, "month": 8},
            headers={"Origin": "http://localhost:3000"},
        )
    assert response.status_code == (500 if storage else 503)
    assert response.json() == {
        "detail": "Internal server error" if storage else "Temporarily unavailable"
    }
    assert response.headers.get("Retry-After") == (None if storage else "5")
    assert "Retry-After" in response.headers["Access-Control-Expose-Headers"]
    table = dynamodb_resource.Table(test_settings.table_name("fetch-log"))
    assert "Item" not in table.get_item(
        Key={"station_id": 47662, "year_month": "2024-08"}
    )
    mock_temperature_data_source.set_response(2024, 8, SAMPLE_JMA_HTML)
    retry = await client.get(
        "/api/temperature/47662/fetch-month", params={"year": 2024, "month": 8}
    )
    assert retry.status_code == 200


async def test_guard_db_failure_is_500_without_upstream_or_release(
    client: AsyncClient,
    mock_temperature_data_source: MockTemperatureDataSource,
) -> None:
    from app.application.temperature.ports.outbound.fetch_guard import (
        GuardStorageUnavailable,
    )
    from app.infrastructure.repositories.fetch_guard import DynamoDBFetchGuard

    with (
        patch.object(
            DynamoDBFetchGuard, "acquire", return_value=GuardStorageUnavailable()
        ),
        patch.object(DynamoDBFetchGuard, "release") as release,
        patch.object(
            mock_temperature_data_source, "fetch_daily_temperatures"
        ) as upstream,
    ):
        response = await client.get(
            "/api/temperature/47662/fetch-month", params={"year": 2024, "month": 8}
        )
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Retry-After" not in response.headers
    upstream.assert_not_called()
    release.assert_not_called()
