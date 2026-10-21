from dataclasses import dataclass
from datetime import datetime
from typing import assert_never
from zoneinfo import ZoneInfo

from app.domain.station.model import Station

FALLBACK_START_YEAR = 1975


@dataclass(frozen=True)
class ObservationPeriodValid:
    pass


@dataclass(frozen=True)
class InvalidObservationPeriod:
    detail: str


def observation_time(now: datetime) -> datetime:
    return now.astimezone(ZoneInfo("Asia/Tokyo"))


def earliest_year(station: Station) -> int:
    return station.earliest_year or FALLBACK_START_YEAR


def validate_year(
    station: Station, year: int, now: datetime
) -> ObservationPeriodValid | InvalidObservationPeriod:
    if not earliest_year(station) <= year <= now.year:
        return InvalidObservationPeriod("year outside observation range")
    return ObservationPeriodValid()


def validate_month(
    station: Station, year: int, month: int, now: datetime
) -> ObservationPeriodValid | InvalidObservationPeriod:
    match validate_year(station, year, now):
        case InvalidObservationPeriod(detail=detail):
            return InvalidObservationPeriod(detail)
        case ObservationPeriodValid():
            pass
        case unreachable:
            assert_never(unreachable)
    if not 1 <= month <= 12 or (year, month) > (now.year, now.month):
        return InvalidObservationPeriod("month outside observation range")
    return ObservationPeriodValid()
