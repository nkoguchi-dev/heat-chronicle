from datetime import datetime, timezone
from typing import Any

import pytest
from boto3.dynamodb.conditions import Key
from httpx import AsyncClient

from app.config import Settings
from integration_tests.fixtures.mock_overrides import MockJmaClient
from integration_tests.fixtures.test_data import (
    SAMPLE_JMA_HTML,
    insert_fetch_log_entry,
    insert_test_temperatures,
)

# ─────────────────────────────────────────────────────────────
# GET /api/temperature/{station_id}
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_temperature_success(
    client: AsyncClient,
    dynamodb_resource: Any,
    test_settings: Settings,
) -> None:
    """キャッシュ済みデータを取得できる。"""
    insert_test_temperatures(dynamodb_resource, test_settings.dynamodb_table_prefix)

    response = await client.get("/api/temperature/47662")

    assert response.status_code == 200
    body = response.json()
    assert "metadata" in body
    assert "data" in body
    assert len(body["data"]) > 0


@pytest.mark.asyncio
async def test_get_temperature_with_end_year(
    client: AsyncClient,
    dynamodb_resource: Any,
    test_settings: Settings,
) -> None:
    """end_year を指定すると metadata.end_year に反映される。"""
    response = await client.get("/api/temperature/47662", params={"end_year": 2023})

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["end_year"] == 2023


@pytest.mark.asyncio
async def test_get_temperature_station_not_found(client: AsyncClient) -> None:
    """存在しない station_id を指定すると 404 が返る。"""
    response = await client.get("/api/temperature/99999")

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_temperature_metadata_structure(
    client: AsyncClient,
    dynamodb_resource: Any,
    test_settings: Settings,
) -> None:
    """metadata に全必須フィールドが含まれる。"""
    insert_test_temperatures(dynamodb_resource, test_settings.dynamodb_table_prefix)

    response = await client.get("/api/temperature/47662")

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert "station_id" in metadata
    assert "station_name" in metadata
    assert "start_year" in metadata
    assert "end_year" in metadata
    assert "total_records" in metadata
    assert "fetched_months" in metadata
    assert "fetching_required" in metadata
    assert "has_older_data" in metadata
    assert "next_end_year" in metadata
    assert metadata["station_id"] == 47662
    assert metadata["station_name"] == "東京"


@pytest.mark.asyncio
async def test_get_temperature_empty_data(client: AsyncClient) -> None:
    """データが存在しない場合、data は空配列で fetching_required は True になる。"""
    response = await client.get("/api/temperature/47662")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["metadata"]["fetching_required"] is True


@pytest.mark.asyncio
async def test_get_temperature_fetching_required_when_unfetched(
    client: AsyncClient,
) -> None:
    """fetch-log が存在しない場合、fetching_required は True になる。"""
    response = await client.get("/api/temperature/47662")

    assert response.status_code == 200
    assert response.json()["metadata"]["fetching_required"] is True


@pytest.mark.asyncio
async def test_get_temperature_has_older_data(client: AsyncClient) -> None:
    """東京（earliest_year=1875）は end_year=2024 時点で has_older_data が True になる。
    CHUNK_SIZE=50 のため start_year=1975 > 1875 (earliest_year) → has_older_data=True。
    """
    response = await client.get("/api/temperature/47662", params={"end_year": 2024})

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["has_older_data"] is True
    assert metadata["next_end_year"] is not None


# ─────────────────────────────────────────────────────────────
# GET /api/temperature/{station_id}/fetch-month
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_month_success(
    client: AsyncClient,
    mock_jma_client: MockJmaClient,
) -> None:
    """新規月のスクレイピングが成功し、records にデータが返る。"""
    mock_jma_client.set_response(2024, 8, SAMPLE_JMA_HTML)

    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 8},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["records"]) > 0


@pytest.mark.asyncio
async def test_fetch_month_cached(
    client: AsyncClient,
    dynamodb_resource: Any,
    test_settings: Settings,
) -> None:
    """フェッチ済み（FINALIZED）の月は JmaClient を呼び出さず DB からデータを返す。
    mock_jma_client にレスポンスを設定せず、もし呼ばれれば RuntimeError になる。
    """
    # 2024-08 の finalize_line は 2024-09-02。それ以降の fetched_at → FINALIZED
    fetched_at = datetime(2024, 10, 1, tzinfo=timezone.utc)
    insert_fetch_log_entry(
        dynamodb_resource,
        test_settings.dynamodb_table_prefix,
        station_id=47662,
        year=2024,
        month=8,
        fetched_at=fetched_at,
    )
    insert_test_temperatures(dynamodb_resource, test_settings.dynamodb_table_prefix)

    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 8},
    )

    # JmaClient が呼ばれていれば RuntimeError → 500 になるため、200 であれば未呼び出し
    assert response.status_code == 200
    body = response.json()
    assert len(body["records"]) > 0


@pytest.mark.asyncio
async def test_fetch_month_station_not_found(client: AsyncClient) -> None:
    """存在しない station_id を指定すると 404 が返る。"""
    response = await client.get(
        "/api/temperature/99999/fetch-month",
        params={"year": 2024, "month": 8},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_fetch_month_invalid_month(client: AsyncClient) -> None:
    """month=13 を指定すると 400 が返る。"""
    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 13},
    )

    assert response.status_code == 400
    assert "month must be 1-12" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fetch_month_invalid_month_zero(client: AsyncClient) -> None:
    """month=0 を指定すると 400 が返る。"""
    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 0},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_fetch_month_future_month(client: AsyncClient) -> None:
    """未来の年月を指定すると 200 で records が空配列になる。"""
    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2027, "month": 1},
    )

    assert response.status_code == 200
    assert response.json()["records"] == []


@pytest.mark.asyncio
async def test_fetch_month_db_side_effects(
    client: AsyncClient,
    dynamodb_resource: Any,
    test_settings: Settings,
    mock_jma_client: MockJmaClient,
) -> None:
    """スクレイピング後、daily-temperature と fetch-log にデータが書き込まれる。"""
    mock_jma_client.set_response(2024, 8, SAMPLE_JMA_HTML)

    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 8},
    )

    assert response.status_code == 200
    assert len(response.json()["records"]) > 0

    # daily-temperature テーブルの検証
    temp_table = dynamodb_resource.Table(test_settings.table_name("daily-temperature"))
    result = temp_table.query(
        KeyConditionExpression=(
            Key("station_id").eq(47662)
            & Key("date").between("2024-08-01", "2024-08-31")
        )
    )
    assert result["Count"] > 0

    # fetch-log テーブルの検証
    log_table = dynamodb_resource.Table(test_settings.table_name("fetch-log"))
    log_result = log_table.get_item(Key={"station_id": 47662, "year_month": "2024-08"})
    assert "Item" in log_result
    assert "fetched_at" in log_result["Item"]


@pytest.mark.asyncio
async def test_fetch_month_response_structure(
    client: AsyncClient,
    mock_jma_client: MockJmaClient,
) -> None:
    """レスポンスに year、month、records が含まれ、各レコードに必要フィールドがある。"""
    mock_jma_client.set_response(2024, 8, SAMPLE_JMA_HTML)

    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 8},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2024
    assert body["month"] == 8
    assert isinstance(body["records"], list)
    assert len(body["records"]) > 0

    for record in body["records"]:
        assert "date" in record
        assert "max_temp" in record
        assert "min_temp" in record
        assert "avg_temp" in record
