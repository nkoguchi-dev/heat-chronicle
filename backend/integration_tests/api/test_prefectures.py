import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_prefectures_returns_all(client: AsyncClient) -> None:
    """全都道府県・地方が返却される。"""
    response = await client.get("/api/prefectures/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 61


@pytest.mark.asyncio
async def test_get_prefectures_structure(client: AsyncClient) -> None:
    """レスポンスの各要素に prec_no（int）と name（str）が含まれる。"""
    response = await client.get("/api/prefectures/")

    assert response.status_code == 200
    data = response.json()
    for prefecture in data:
        assert isinstance(prefecture["prec_no"], int)
        assert isinstance(prefecture["name"], str)
        assert len(prefecture["name"]) > 0


@pytest.mark.asyncio
async def test_get_prefectures_includes_tokyo(client: AsyncClient) -> None:
    """東京都（prec_no=44）が含まれている。"""
    response = await client.get("/api/prefectures/")

    assert response.status_code == 200
    data = response.json()
    tokyo = next((p for p in data if p["prec_no"] == 44), None)
    assert tokyo is not None
    assert tokyo["name"] == "東京都"
