from typing import get_args, get_type_hints

from app.application.temperature.get_temperature_use_case import (
    GetTemperatureDataOutput,
    TemperatureRecordOutput,
)


def test_get_temperature_data_output_uses_application_record_dto() -> None:
    data_type = get_type_hints(GetTemperatureDataOutput)["data"]

    assert get_args(data_type) == (TemperatureRecordOutput,)
