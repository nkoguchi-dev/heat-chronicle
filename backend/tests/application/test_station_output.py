from typing import get_args, get_type_hints

from app.application.station.service import StationOutput, StationService


def test_station_service_uses_application_output_dto() -> None:
    return_type = get_type_hints(StationService.get_stations)["return"]

    assert get_args(return_type) == (StationOutput,)
