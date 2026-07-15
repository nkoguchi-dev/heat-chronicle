from typing import get_args, get_type_hints

from app.application.station.get_station_use_case import GetStationUseCase, StationOutput


def test_get_station_use_case_uses_application_output_dto() -> None:
    return_type = get_type_hints(GetStationUseCase.get_stations)["return"]

    assert get_args(return_type) == (StationOutput,)
