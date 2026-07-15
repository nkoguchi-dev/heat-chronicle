from typing import get_args, get_type_hints

from app.application.temperature.fetch_month_use_case import (
    FetchMonthUseCase,
    FetchMonthTemperatureOutput,
)


def test_fetch_month_use_case_uses_output_dto() -> None:
    return_type = get_type_hints(FetchMonthUseCase.fetch_month)["return"]

    assert get_args(return_type) == (FetchMonthTemperatureOutput,)
