from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Wall time for calendar/expiry, monotonic time for local elapsed durations."""

    def now(self) -> datetime:
        """Return a timezone-aware UTC timestamp."""
        ...

    def monotonic(self) -> float:
        """Return elapsed seconds unaffected by wall-clock adjustments."""
        ...
