from datetime import datetime, timezone

import pytest

from app.domain.station.model import Station
from app.domain.temperature.input_policy import (
    InvalidObservationPeriod,
    ObservationPeriodValid,
    validate_year,
)


@pytest.mark.parametrize(
    "year,valid", [(1871, False), (1872, True), (2026, True), (2027, False)]
)
def test_year_validation_is_a_pure_result(year: int, valid: bool) -> None:
    result = validate_year(
        Station(4, "Tokyo", 44, "47662", "s", earliest_year=1872),
        year,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    if valid:
        assert isinstance(result, ObservationPeriodValid)
    else:
        assert result == InvalidObservationPeriod("year outside observation range")


@pytest.mark.parametrize(
    "year,month,detail",
    [
        (1871, 0, "year outside observation range"),
        (2026, 0, "month outside observation range"),
        (2026, 13, "month outside observation range"),
        (2026, 2, "month outside observation range"),
        (1872, 1, None),
        (2026, 1, None),
    ],
)
def test_month_validation_keeps_year_priority(
    year: int, month: int, detail: str | None
) -> None:
    from app.domain.temperature.input_policy import validate_month

    result = validate_month(
        Station(4, "Tokyo", 44, "47662", "s", earliest_year=1872),
        year,
        month,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert result == (
        ObservationPeriodValid() if detail is None else InvalidObservationPeriod(detail)
    )
