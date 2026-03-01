import calendar
from datetime import datetime, timedelta
from enum import Enum


class FetchStatus(Enum):
    UNFETCHED = "unfetched"
    NEEDS_REFRESH = "needs_refresh"
    TEMPORARILY_CACHED = "temporarily_cached"
    FINALIZED = "finalized"


class FetchFreshnessPolicy:
    GRACE_PERIOD_DAYS: int = 2
    TEMPORARY_CACHE_TTL_HOURS: int = 24

    def evaluate(
        self,
        year: int,
        month: int,
        fetched_at: datetime | None,
        now: datetime,
    ) -> FetchStatus:
        if fetched_at is None:
            return FetchStatus.UNFETCHED

        last_day = calendar.monthrange(year, month)[1]
        finalize_line = datetime(
            year, month, last_day, tzinfo=fetched_at.tzinfo
        ) + timedelta(days=self.GRACE_PERIOD_DAYS)

        if fetched_at > finalize_line:
            return FetchStatus.FINALIZED

        if now - fetched_at < timedelta(hours=self.TEMPORARY_CACHE_TTL_HOURS):
            return FetchStatus.TEMPORARILY_CACHED

        return FetchStatus.NEEDS_REFRESH
