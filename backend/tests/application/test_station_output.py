from typing import get_args, get_type_hints

from app.application.station.list_station_use_case import (
    ListStationUseCase,
    StationOutput,
)


def test_list_station_use_case_uses_application_output_dto() -> None:
    return_type = get_type_hints(ListStationUseCase.list_stations)["return"]

    assert get_args(return_type) == (StationOutput,)
