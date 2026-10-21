from typing import Protocol


class FetchUnavailable(Exception):
    """Upstream capacity or time budget is unavailable."""


class FetchGuard(Protocol):
    def acquire(self) -> None: ...

    def check_owner(self) -> None: ...

    async def before_attempt(self) -> None: ...

    def release(self) -> None: ...
