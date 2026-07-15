from datetime import date

import pytest
from pydantic import ValidationError

from app.presentation.api.shared.internal_server_error import (
    InternalServerErrorResponse,
)
from app.presentation.api.stations.get_stations import StationResponse
from app.presentation.api.temperature.fetch_month import (
    MonthTemperatureRecordResponse,
)
from app.presentation.api.temperature.get_temperature import (
    TemperatureRecordResponse,
)


def test_station_response_rejects_implicit_number_conversion() -> None:
    with pytest.raises(ValidationError):
        StationResponse.model_validate(
            {
                "id": "47662",
                "station_name": "東京",
                "prec_no": 44,
                "block_no": "47662",
                "station_type": "s",
            }
        )


def test_internal_server_error_response_is_strict() -> None:
    with pytest.raises(ValidationError):
        InternalServerErrorResponse.model_validate({"detail": 500})


def test_station_response_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        StationResponse.model_validate(
            {
                "id": 47662,
                "station_name": "東京",
                "prec_no": 44,
                "block_no": "47662",
                "station_type": "s",
                "unexpected": True,
            }
        )


def test_station_response_rejects_invalid_station_type() -> None:
    with pytest.raises(ValidationError):
        StationResponse.model_validate(
            {
                "id": 47662,
                "station_name": "東京",
                "prec_no": 44,
                "block_no": "47662",
                "station_type": "invalid",
            }
        )


def test_temperature_record_response_is_strict() -> None:
    with pytest.raises(ValidationError):
        TemperatureRecordResponse.model_validate(
            {
                "date": "2024-08-01",
                "max_temp": 35.0,
                "min_temp": 25.0,
                "avg_temp": 30.0,
            }
        )

    response = TemperatureRecordResponse(
        date=date(2024, 8, 1),
        max_temp=35.0,
        min_temp=25.0,
        avg_temp=30.0,
    )
    assert response.date == date(2024, 8, 1)


def test_endpoints_do_not_share_temperature_record_dto() -> None:
    assert TemperatureRecordResponse.__name__ != MonthTemperatureRecordResponse.__name__
