from datetime import datetime, timedelta, timezone


class FixedClock:
    def __init__(self, now: datetime | None = None) -> None:
        self.wall_time = (
            now if now is not None else datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        self.elapsed_seconds = 0.0

    def now(self) -> datetime:
        return self.wall_time

    def monotonic(self) -> float:
        return self.elapsed_seconds

    def advance(self, seconds: float) -> None:
        self.wall_time += timedelta(seconds=seconds)
        self.elapsed_seconds += seconds
