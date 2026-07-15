from dataclasses import dataclass
from datetime import date as Date


@dataclass(frozen=True)
class DailyTemperature:
    date: Date
    max_temp: float | None = None
    min_temp: float | None = None
    avg_temp: float | None = None
