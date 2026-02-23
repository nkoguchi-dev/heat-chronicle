"""Fetch the earliest available year for each station from JMA website.

For each station, accesses the JMA station index page and parses the year
hyperlinks to find the minimum available year. Updates stations.json
with an `earliest_year` field.

Usage:
    cd backend && poetry run python ../scripts/fetch_earliest_years.py

Output:
    Updates backend/data/stations.json in-place (adds earliest_year field)
    Also outputs backend/data/earliest_years_YYYYMMDD.csv as a standalone record
"""

import asyncio
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# JMA station index page base URL
# When accessed with prec_no & block_no, shows year hyperlinks with available years
INDEX_URL = "https://www.data.jma.go.jp/obd/stats/etrn/index.php"

INTERVAL_SEC = 2.0
MAX_RETRIES = 3


async def fetch_earliest_year(
    client: httpx.AsyncClient,
    prec_no: int,
    block_no: str,
) -> int | None:
    """Fetch the earliest available year for a station from JMA.

    Accesses the station's index page and extracts year values from
    hyperlinks (e.g. index.php?...&year=YYYY&...) to find the minimum year.

    Returns the earliest year as int, or None if it could not be determined.
    """
    params = {
        "prec_no": prec_no,
        "block_no": block_no,
        "year": "",
        "month": "",
        "day": "",
        "view": "",
    }

    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(INDEX_URL, params=params)
            resp.raise_for_status()
            break
        except httpx.HTTPError as e:
            last_exc = e
            wait = 2 ** (attempt + 1)
            print(f"    Retry {attempt + 1}/{MAX_RETRIES} after error: {e}, "
                  f"waiting {wait}s")
            await asyncio.sleep(wait)
    else:
        print(f"    Failed after {MAX_RETRIES} retries: {last_exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # JMA pages display years as hyperlinks (e.g. [2026年] [2025年] ... [1872年])
    # Each link has href like index.php?prec_no=44&block_no=47662&year=YYYY&...
    years: list[int] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        match = re.search(r"[?&]year=(\d{4})", href)
        if match:
            years.append(int(match.group(1)))

    if not years:
        print(f"    No year links found on the page")
        return None

    return min(years)


async def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "backend" / "data"
    stations_path = data_dir / "stations.json"

    if not stations_path.exists():
        print(f"Error: {stations_path} not found")
        sys.exit(1)

    with open(stations_path, encoding="utf-8") as f:
        stations = json.load(f)

    print(f"Loaded {len(stations)} stations from {stations_path}")

    # Track results
    success_count = 0
    fail_count = 0
    results: list[dict] = []

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "heat-chronicle/1.0"},
        follow_redirects=True,
    ) as client:
        for i, station in enumerate(stations):
            station_name = station["station_name"]
            prec_no = station["prec_no"]
            block_no = station["block_no"]

            print(
                f"[{i + 1}/{len(stations)}] "
                f"{station_name} (prec_no={prec_no}, block_no={block_no})"
            )

            earliest_year = await fetch_earliest_year(client, prec_no, block_no)

            if earliest_year is not None:
                station["earliest_year"] = earliest_year
                success_count += 1
                print(f"    -> earliest_year: {earliest_year}")
            else:
                fail_count += 1
                print(f"    -> FAILED to determine earliest_year")

            results.append({
                "id": station.get("id"),
                "station_name": station_name,
                "prec_no": prec_no,
                "block_no": block_no,
                "station_type": station.get("station_type"),
                "earliest_year": earliest_year,
            })

            # Rate limiting
            if i < len(stations) - 1:
                await asyncio.sleep(INTERVAL_SEC)

    # Save updated stations.json
    with open(stations_path, "w", encoding="utf-8") as f:
        json.dump(stations, f, ensure_ascii=False, indent=2)
    print(f"\nUpdated {stations_path} with earliest_year field")

    # Save CSV report
    today = date.today().strftime("%Y%m%d")
    csv_path = data_dir / f"earliest_years_{today}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id", "station_name", "prec_no", "block_no",
                "station_type", "earliest_year",
            ],
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"Wrote CSV report to {csv_path}")

    # Summary
    print(f"\nSummary: {success_count} succeeded, {fail_count} failed "
          f"out of {len(stations)} stations")

    if fail_count > 0:
        print("\nFailed stations:")
        for r in results:
            if r["earliest_year"] is None:
                print(f"  - {r['station_name']} "
                      f"(prec_no={r['prec_no']}, block_no={r['block_no']})")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
