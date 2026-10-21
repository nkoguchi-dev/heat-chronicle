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
