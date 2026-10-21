from datetime import date

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.application.temperature.ports.inbound.get_temperature import (
    GetTemperatureDataOutput,
    GetTemperaturePort,
    TemperatureMetadataOutput,
    TemperatureRecordOutput,
)
from app.di.container import register_dependencies
from app.presentation.api.shared.dependencies import get_temperature_port
from app.presentation.api.temperature.get_temperature import router


async def test_temperature_port_override_keeps_query_and_response_boundary() -> None:
    calls: list[tuple[int, int | None]] = []

    class FakeTemperaturePort:
        def get_temperature_data(
            self, station_id: int, end_year: int | None
        ) -> GetTemperatureDataOutput:
            calls.append((station_id, end_year))
            return GetTemperatureDataOutput(
                TemperatureMetadataOutput(
                    4, "東京", 1975, 2024, 1, [], True, True, 1974
                ),
                [TemperatureRecordOutput(date(2024, 1, 1))],
            )

    def provider() -> GetTemperaturePort:
        return FakeTemperaturePort()

    app = FastAPI()
    app.include_router(router, prefix="/api/temperature")
    register_dependencies(app)
    app.dependency_overrides[get_temperature_port] = provider
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/temperature/4?end_year=2024")
    assert response.status_code == 200
    assert calls == [(4, 2024)]
    assert response.json()["data"] == [
        {"date": "2024-01-01", "max_temp": None, "min_temp": None, "avg_temp": None}
    ]
