from dataclasses import dataclass


@dataclass(frozen=True)
class Prefecture:
    """JMA region number and name, including Hokkaido districts and Antarctica."""

    prec_no: int
    name: str
