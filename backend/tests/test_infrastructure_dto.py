from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.infrastructure.dto.dynamodb import (
    DailyTemperatureItemDTO,
    FetchLogItemDTO,
    StationItemDTO,
    StationSeedDTO,
)
from app.infrastructure.dto.jma import (
    JmaDailyPageRequestDTO,
    JmaDailyTemperatureDTO,
)


def test_station_item_accepts_dynamodb_types() -> None:
    dto = StationItemDTO.model_validate(
        {
            "id": Decimal("1"),
            "station_name": "東京",
            "prec_no": Decimal("44"),
            "block_no": "47662",
            "station_type": "s",
            "earliest_year": Decimal("1875"),
        }
    )

    assert dto.id == Decimal("1")
    assert dto.earliest_year == Decimal("1875")


def test_station_item_rejects_implicit_number_conversion() -> None:
    with pytest.raises(ValidationError):
        StationItemDTO.model_validate(
            {
                "id": "1",
                "station_name": "東京",
                "prec_no": Decimal("44"),
                "block_no": "47662",
                "station_type": "s",
            }
        )


def test_station_item_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        StationItemDTO.model_validate(
            {
                "id": Decimal("1"),
                "station_name": "東京",
                "prec_no": Decimal("44"),
                "block_no": "47662",
                "station_type": "s",
                "unexpected": True,
            }
        )


def test_station_seed_rejects_invalid_station_type() -> None:
    with pytest.raises(ValidationError):
        StationSeedDTO.model_validate(
            {
                "id": 1,
                "station_name": "東京",
                "prec_no": 44,
                "block_no": "47662",
                "station_type": "invalid",
            }
        )


def test_daily_temperature_item_rejects_invalid_date() -> None:
    with pytest.raises(ValidationError):
        DailyTemperatureItemDTO.model_validate(
            {
                "station_id": Decimal("47662"),
                "date": "2024-02-30",
            }
        )


def test_fetch_log_item_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        FetchLogItemDTO.model_validate(
            {
                "station_id": Decimal("47662"),
                "year_month": "2024-08",
                "fetched_at": "2024-10-01T00:00:00",
            }
        )


def test_jma_request_rejects_out_of_range_month() -> None:
    with pytest.raises(ValidationError):
        JmaDailyPageRequestDTO(
            prec_no=44,
            block_no="47662",
            year=2024,
            month=13,
            station_type="s",
        )


def test_jma_temperature_rejects_string_date_in_strict_mode() -> None:
    with pytest.raises(ValidationError):
        JmaDailyTemperatureDTO.model_validate(
            {
                "date": "2024-08-01",
                "max_temp": 35.0,
                "min_temp": 25.0,
                "avg_temp": 30.0,
            }
        )

    dto = JmaDailyTemperatureDTO(
        date=date(2024, 8, 1),
        max_temp=35.0,
        min_temp=25.0,
        avg_temp=30.0,
    )
    assert dto.date == date(2024, 8, 1)
