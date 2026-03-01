import pytest
from httpx import AsyncClient

from integration_tests.fixtures.test_data import TEST_STATIONS


@pytest.mark.asyncio
async def test_get_all_stations(client: AsyncClient) -> None:
    """全観測地点一覧を取得できる。"""
    response = await client.get("/api/stations/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    returned_ids = {s["id"] for s in data}
    for station in TEST_STATIONS:
        assert station["id"] in returned_ids


@pytest.mark.asyncio
async def test_get_stations_by_prec_no(client: AsyncClient) -> None:
    """prec_no=44 で東京の地点のみ返却される。"""
    response = await client.get("/api/stations/", params={"prec_no": 44})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for station in data:
        assert station["prec_no"] == 44


@pytest.mark.asyncio
async def test_get_stations_by_prec_no_empty(client: AsyncClient) -> None:
    """存在しない prec_no を指定すると空配列が返却される。"""
    response = await client.get("/api/stations/", params={"prec_no": 99999})

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_get_stations_response_structure(client: AsyncClient) -> None:
    """レスポンスの各要素に必要なフィールドが含まれる。"""
    response = await client.get("/api/stations/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    for station in data:
        assert isinstance(station["id"], int)
        assert isinstance(station["station_name"], str)
        assert isinstance(station["prec_no"], int)
        assert isinstance(station["block_no"], str)
        assert isinstance(station["station_type"], str)


@pytest.mark.asyncio
async def test_get_stations_includes_earliest_year(client: AsyncClient) -> None:
    """earliest_year フィールドが含まれ、int または null である。"""
    response = await client.get("/api/stations/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    for station in data:
        assert "earliest_year" in station
        assert station["earliest_year"] is None or isinstance(
            station["earliest_year"], int
        )
