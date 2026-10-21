from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PrefectureOutput:
    prec_no: int
    name: str


class ListPrefecturePort(Protocol):
    def list_prefectures(self) -> list[PrefectureOutput]: ...
