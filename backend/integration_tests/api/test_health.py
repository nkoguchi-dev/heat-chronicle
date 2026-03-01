import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """ヘルスチェックエンドポイントが正常に応答する。"""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
