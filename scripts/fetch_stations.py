"""Fetch all JMA weather stations with temperature observations.

Usage:
    cd backend && poetry run python ../scripts/fetch_stations.py

Output:
    backend/data/stations_YYYYMMDD.csv
"""

import asyncio
import csv
import re
import sys
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.data.jma.go.jp/obd/stats/etrn/select"
INTERVAL_SEC = 2.0


async def fetch_prefectures(client: httpx.AsyncClient) -> list[tuple[int, str]]:
    """Fetch prefecture list from JMA top page.

    Returns list of (prec_no, prefecture_name).
    """
    url = f"{BASE_URL}/prefecture00.php"
    resp = await client.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    prefectures: list[tuple[int, str]] = []

    for area in soup.find_all("area"):
        href = area.get("href", "")
        alt = area.get("alt", "")
        match = re.search(r"prec_no=(\d+)", href)
        if match and alt:
            prec_no = int(match.group(1))
            prefectures.append((prec_no, alt))

    return prefectures


async def fetch_stations_for_prefecture(
    client: httpx.AsyncClient, prec_no: int
) -> list[dict[str, str | int]]:
    """Fetch stations for a prefecture that have temperature observations.

    Parses onmouseover="viewPoint(...)" from <area> tags.
    """
    url = f"{BASE_URL}/prefecture.php?prec_no={prec_no}"
    resp = await client.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    stations: list[dict[str, str | int]] = []
    seen_block_nos: set[str] = set()

    for area in soup.find_all("area"):
        onmouseover = area.get("onmouseover", "")
        # viewPoint('s','47662','東京',...) or viewPoint('a','0363','さいたま',...)
        # Format: viewPoint(type, block_no, name, ..., f_temp, ...)
        match = re.search(r"viewPoint\((.*?)\)", onmouseover)
        if not match:
            continue

        # Parse arguments - they are comma-separated, quoted with single quotes
        args_str = match.group(1)
        args = [a.strip().strip("'") for a in args_str.split(",")]

        if len(args) < 11:
            continue

        station_type = args[0]  # 's' or 'a'
        block_no = args[1]
        station_name = args[2]

        # viewPoint args layout (both 's' and 'a'):
        # 0:type, 1:block_no, 2:name, 3:kana,
        # 4:lat_deg, 5:lat_min, 6:lon_deg, 7:lon_min, 8:height,
        # 9:f_prec, 10:f_temp, 11:f_wind, ...
        if station_type not in ("s", "a"):
            continue

        f_temp_idx = 10

        if f_temp_idx >= len(args):
            continue

        try:
            f_temp = int(args[f_temp_idx])
        except (ValueError, IndexError):
            continue

        if f_temp < 1:
            continue

        if block_no in seen_block_nos:
            continue
        seen_block_nos.add(block_no)

        stations.append(
            {
                "prec_no": prec_no,
                "station_name": station_name,
                "block_no": block_no,
                "station_type": station_type,
            }
        )

    return stations


async def main() -> None:
    output_dir = Path(__file__).resolve().parent.parent / "backend" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    output_path = output_dir / f"stations_{today}.csv"

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "heat-chronicle/1.0"},
        follow_redirects=True,
    ) as client:
        print("Fetching prefecture list...")
        prefectures = await fetch_prefectures(client)
        print(f"Found {len(prefectures)} prefectures")

        all_stations: list[dict[str, str | int]] = []

        for i, (prec_no, pref_name) in enumerate(prefectures):
            print(
                f"[{i + 1}/{len(prefectures)}] "
                f"Fetching stations for {pref_name} (prec_no={prec_no})..."
            )
            stations = await fetch_stations_for_prefecture(client, prec_no)
            print(f"  Found {len(stations)} stations with temperature data")
            all_stations.extend(stations)

            if i < len(prefectures) - 1:
                await asyncio.sleep(INTERVAL_SEC)

    # Sort by prec_no, then station_name
    all_stations.sort(key=lambda s: (s["prec_no"], s["station_name"]))

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["prec_no", "station_name", "block_no", "station_type"]
        )
        writer.writeheader()
        writer.writerows(all_stations)

    print(f"\nWrote {len(all_stations)} stations to {output_path}")

    # Also output prefecture mapping for prefectures.py
    pref_path = output_dir / f"prefectures_{today}.txt"
    prefectures.sort(key=lambda p: p[0])
    with open(pref_path, "w", encoding="utf-8") as f:
        f.write("PREFECTURES: dict[int, str] = {\n")
        for prec_no, name in prefectures:
            f.write(f'    {prec_no}: "{name}",\n')
        f.write("}\n")
    print(f"Wrote prefecture mapping to {pref_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
