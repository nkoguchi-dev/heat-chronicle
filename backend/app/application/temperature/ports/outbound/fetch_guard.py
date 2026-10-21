from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GuardSucceeded:
    pass


@dataclass(frozen=True)
class LeaseBusy:
    pass


@dataclass(frozen=True)
class LeaseLost:
    pass


@dataclass(frozen=True)
class GuardStorageUnavailable:
    pass


class FetchGuard(Protocol):
    def acquire(self) -> GuardSucceeded | LeaseBusy | GuardStorageUnavailable: ...

    def check_owner(self) -> GuardSucceeded | LeaseLost | GuardStorageUnavailable: ...

    async def before_attempt(
        self,
    ) -> GuardSucceeded | LeaseLost | GuardStorageUnavailable: ...

    def release(self) -> GuardSucceeded | GuardStorageUnavailable: ...
