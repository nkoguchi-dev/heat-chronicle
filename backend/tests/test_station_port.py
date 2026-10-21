import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.application.station.ports.inbound.list_station import (
    ListStationPort,
    PrefectureNotFound,
    StationOutput,
)
from app.di.container import get_station_repository, register_dependencies
from app.domain.station.model import Station
from app.presentation.api.shared.dependencies import get_station_port
from app.presentation.api.stations.get_stations import router


class FakeStationPort:
    def __init__(self) -> None:
        self.received: list[int | None] = []

    def list_stations(self, prec_no: int | None = None) -> list[StationOutput]:
        self.received.append(prec_no)
        if prec_no == 99999:
            raise PrefectureNotFound("Prefecture not found")
        return [StationOutput(1, "地点", 44, "0001", "a")]


def routed_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/stations")
    register_dependencies(app)
    return app


@pytest.mark.parametrize("prec_no", [None, 44])
async def test_endpoint_uses_inbound_port_and_maps_output(prec_no: int | None) -> None:
    app = routed_app()
    fake = FakeStationPort()

    def provider() -> ListStationPort:
        return fake

    app.dependency_overrides[get_station_port] = provider
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/stations/", params={} if prec_no is None else {"prec_no": prec_no}
        )
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "station_name": "地点",
            "prec_no": 44,
            "block_no": "0001",
            "station_type": "a",
            "latitude": None,
            "longitude": None,
            "earliest_year": None,
        }
    ]
    assert fake.received == [prec_no]


async def test_inbound_not_found_maps_to_existing_404() -> None:
    app = routed_app()
    app.dependency_overrides[get_station_port] = FakeStationPort
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/stations/", params={"prec_no": 99999})
    assert response.status_code == 404
    assert response.json() == {"detail": "Prefecture not found"}


async def test_real_di_connects_use_case_to_outbound_port() -> None:
    # A fake repository satisfies the Outbound Port without boto3/AWS.
    class EmptyRepository:
        def get_all(self) -> list[Station]:
            return []

        def get_by_prec_no(self, prec_no: int) -> list[Station]:
            return []

        def get_by_id(self, station_id: int) -> Station | None:
            return None

    app = routed_app()
    app.dependency_overrides[get_station_repository] = EmptyRepository
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/stations/")
    assert response.status_code == 200
    assert response.json() == []
