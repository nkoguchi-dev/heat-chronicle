from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import partial
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from bs4.element import ResultSet, Tag


@dataclass
class DailyRecord:
    date: date
    max_temp: float | None
    min_temp: float | None
    avg_temp: float | None


# Pattern to strip quality flags like ], ), *, #
QUALITY_FLAG_RE = re.compile(r"[\]\)\*#\s]")

S_TYPE_AVG_COL = 6
S_TYPE_MAX_COL = 7
S_TYPE_MIN_COL = 8

A_TYPE_AVG_COL = 4
A_TYPE_MAX_COL = 5
A_TYPE_MIN_COL = 6


def _parse_temp(value: str) -> float | None:
    """Parse a temperature cell value, returning None for missing data."""
    cleaned = QUALITY_FLAG_RE.sub("", value).strip()
    if not cleaned or cleaned in ("--", "×", "///"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_row(
    cells: ResultSet[Tag],
    avg_col: int,
    max_col: int,
    min_col: int,
) -> tuple[float | None, float | None, float | None] | None:
    if len(cells) < min_col + 1:
        return None
    avg_temp = _parse_temp(cells[avg_col].get_text(strip=True))
    max_temp = _parse_temp(cells[max_col].get_text(strip=True))
    min_temp = _parse_temp(cells[min_col].get_text(strip=True))
    return avg_temp, max_temp, min_temp


def parse_daily_page(
    html: str, year: int, month: int, station_type: str
) -> list[DailyRecord]:
    """Parse a JMA daily data page and extract temperature records."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="data2_s")
    if table is None:
        return []

    records: list[DailyRecord] = []
    tbody = table.find("tbody") or table

    if station_type == "s":
        parse_row = partial(
            _parse_row,
            avg_col=S_TYPE_AVG_COL,
            max_col=S_TYPE_MAX_COL,
            min_col=S_TYPE_MIN_COL,
        )
    else:
        parse_row = partial(
            _parse_row,
            avg_col=A_TYPE_AVG_COL,
            max_col=A_TYPE_MAX_COL,
            min_col=A_TYPE_MIN_COL,
        )

    for tr in tbody.find_all("tr", class_="mtx"):
        cells = tr.find_all("td")
        if not cells:
            continue

        # First cell is the day number
        day_text = cells[0].get_text(strip=True)
        try:
            day = int(day_text)
        except ValueError:
            continue

        try:
            record_date = date(year, month, day)
        except ValueError:
            continue

        temps = parse_row(cells)
        if temps is None:
            continue

        avg_temp, max_temp, min_temp = temps
        records.append(
            DailyRecord(
                date=record_date,
                max_temp=max_temp,
                min_temp=min_temp,
                avg_temp=avg_temp,
            )
        )

    return records
