import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup


@dataclass
class DailyRecord:
    date: date
    max_temp: float | None
    min_temp: float | None
    avg_temp: float | None


# Pattern to strip quality flags like ], ), *, #
QUALITY_FLAG_RE = re.compile(r"[\]\)\*#\s]")


def _parse_temp(value: str) -> float | None:
    """Parse a temperature cell value, returning None for missing data."""
    cleaned = QUALITY_FLAG_RE.sub("", value).strip()
    if not cleaned or cleaned in ("--", "×", "///"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


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

        if station_type == "s":
            # daily_s1.php: columns vary but temperature block is after
            # pressure/precipitation. Typical indices:
            # avg_temp=6, max_temp=7, min_temp=8 (0-indexed from first td)
            if len(cells) < 9:
                continue
            avg_temp = _parse_temp(cells[6].get_text(strip=True))
            max_temp = _parse_temp(cells[7].get_text(strip=True))
            min_temp = _parse_temp(cells[8].get_text(strip=True))
        else:
            # daily_a1.php (AMEDAS): fewer columns
            # avg_temp=4, max_temp=5, min_temp=6 (typical layout)
            if len(cells) < 7:
                continue
            avg_temp = _parse_temp(cells[4].get_text(strip=True))
            max_temp = _parse_temp(cells[5].get_text(strip=True))
            min_temp = _parse_temp(cells[6].get_text(strip=True))

        records.append(
            DailyRecord(
                date=record_date,
                max_temp=max_temp,
                min_temp=min_temp,
                avg_temp=avg_temp,
            )
        )

    return records
