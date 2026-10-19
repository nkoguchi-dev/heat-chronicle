from datetime import datetime
from zoneinfo import ZoneInfo

from app.domain.station.model import Station

FALLBACK_START_YEAR = 1975


class InvalidTemperatureInput(ValueError):
    pass


def observation_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Tokyo"))


def earliest_year(station: Station) -> int:
    return station.earliest_year or FALLBACK_START_YEAR


def validate_year(station: Station, year: int, now: datetime) -> None:
    if not earliest_year(station) <= year <= now.year:
        raise InvalidTemperatureInput("year outside observation range")


def validate_month(station: Station, year: int, month: int, now: datetime) -> None:
    validate_year(station, year, now)
    if not 1 <= month <= 12 or (year, month) > (now.year, now.month):
        raise InvalidTemperatureInput("month outside observation range")
