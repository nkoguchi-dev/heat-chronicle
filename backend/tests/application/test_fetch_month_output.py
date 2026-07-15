from typing import get_args, get_type_hints

from app.application.temperature.scrape_service import (
    FetchMonthTemperatureOutput,
    ScrapeService,
)


def test_scrape_service_uses_fetch_month_output_dto() -> None:
    return_type = get_type_hints(ScrapeService.fetch_month)["return"]

    assert get_args(return_type) == (FetchMonthTemperatureOutput,)
