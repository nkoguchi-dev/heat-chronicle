from typing import get_args, get_type_hints

import pytest

from app.application.station.list_station_use_case import ListStationUseCase
from app.application.station.ports.inbound.list_station import (
    PrefectureNotFound,
    StationOutput,
)
from app.domain.station.model import Station


def test_list_station_use_case_uses_application_output_dto() -> None:
    return_type = get_type_hints(ListStationUseCase.list_stations)["return"]

    assert get_args(return_type) == (StationOutput,)


class MemoryStationRepository:
    def __init__(self, stations: list[Station]) -> None:
        self.stations = stations
        self.calls: list[int | None] = []

    def get_all(self) -> list[Station]:
        self.calls.append(None)
        return self.stations

    def get_by_prec_no(self, prec_no: int) -> list[Station]:
        self.calls.append(prec_no)
        return [station for station in self.stations if station.prec_no == prec_no]

    def get_by_id(self, station_id: int) -> Station | None:
        return next(
            (station for station in self.stations if station.id == station_id), None
        )


@pytest.mark.parametrize("prec_no", [None, 44])
def test_station_use_case_maps_domain_to_output(prec_no: int | None) -> None:
    station = Station(4, "東京", 44, "47662", "s", 35.69, 139.75, 1872)
    repo = MemoryStationRepository([station])
    output = ListStationUseCase(repo).list_stations(prec_no)
    assert output == [StationOutput(4, "東京", 44, "47662", "s", 35.69, 139.75, 1872)]
    assert type(output[0]) is StationOutput
    assert repo.calls == [prec_no]


def test_station_use_case_preserves_null_fields() -> None:
    repo = MemoryStationRepository([Station(1, "地点", 44, "0001", "a")])
    assert ListStationUseCase(repo).list_stations() == [
        StationOutput(1, "地点", 44, "0001", "a")
    ]


def test_empty_station_catalog_is_success() -> None:
    assert ListStationUseCase(MemoryStationRepository([])).list_stations() == []


def test_missing_region_uses_inbound_error_contract() -> None:
    with pytest.raises(PrefectureNotFound, match="^Prefecture not found$"):
        ListStationUseCase(MemoryStationRepository([])).list_stations(99999)
