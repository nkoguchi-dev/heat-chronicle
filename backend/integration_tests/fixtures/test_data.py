from datetime import datetime
from decimal import Decimal
from typing import Any

TEST_STATIONS = [
    {
        "id": 47662,
        "station_name": "東京",
        "prec_no": 44,
        "block_no": "47662",
        "station_type": "s",
        "latitude": Decimal("35.6917"),
        "longitude": Decimal("139.7500"),
        "earliest_year": 1875,
    },
    {
        "id": 1001,
        "station_name": "札幌",
        "prec_no": 14,
        "block_no": "47412",
        "station_type": "s",
        "latitude": Decimal("43.0600"),
        "longitude": Decimal("141.3300"),
        "earliest_year": 1876,
    },
]

TEST_TEMPERATURES = [
    {
        "station_id": 47662,
        "date": "2024-08-01",
        "max_temp": Decimal("35.2"),
        "min_temp": Decimal("26.1"),
        "avg_temp": Decimal("30.5"),
    },
    {
        "station_id": 47662,
        "date": "2024-08-02",
        "max_temp": Decimal("34.1"),
        "min_temp": Decimal("25.8"),
        "avg_temp": Decimal("29.8"),
    },
    {
        "station_id": 47662,
        "date": "2024-08-03",
        "max_temp": Decimal("36.0"),
        "min_temp": Decimal("27.0"),
        "avg_temp": Decimal("31.0"),
    },
]


def _make_s1_html(rows: list[tuple[Any, ...]]) -> str:
    """s1 形式の日別気温 HTML を生成する。"""
    row_html = ""
    for row in rows:
        cells = "".join(f"<td>{v}</td>" for v in row)
        row_html += f'<tr class="mtx">{cells}</tr>'
    return f"""
    <html><body>
    <table class="data2_s">
    <tbody>
    <tr class="mtx"><th>日</th></tr>
    {row_html}
    </tbody>
    </table>
    </body></html>
    """


# 2024-08 のサンプル JMA HTML（s1 形式: day, c1..c5, avg, max, min）
SAMPLE_JMA_HTML: str = _make_s1_html(
    [
        (1, "x", "x", "x", "x", "x", "30.5", "35.2", "26.1"),
        (2, "x", "x", "x", "x", "x", "29.8", "34.1", "25.8"),
        (3, "x", "x", "x", "x", "x", "31.0", "36.0", "27.0"),
    ]
)


def insert_test_stations(dynamodb_resource: Any, table_prefix: str) -> None:
    """テスト用の観測地点データを投入する。"""
    table_name = f"{table_prefix}-stations" if table_prefix else "stations"
    table = dynamodb_resource.Table(table_name)
    with table.batch_writer() as batch:
        for station in TEST_STATIONS:
            batch.put_item(Item=station)


def insert_test_temperatures(dynamodb_resource: Any, table_prefix: str) -> None:
    """テスト用の気温データを投入する。"""
    table_name = (
        f"{table_prefix}-daily-temperature" if table_prefix else "daily-temperature"
    )
    table = dynamodb_resource.Table(table_name)
    with table.batch_writer() as batch:
        for record in TEST_TEMPERATURES:
            batch.put_item(Item=record)


def insert_fetch_log_entry(
    dynamodb_resource: Any,
    table_prefix: str,
    station_id: int,
    year: int,
    month: int,
    fetched_at: datetime,
) -> None:
    """フェッチログエントリを投入する。"""
    table_name = f"{table_prefix}-fetch-log" if table_prefix else "fetch-log"
    table = dynamodb_resource.Table(table_name)
    table.put_item(
        Item={
            "station_id": station_id,
            "year_month": f"{year:04d}-{month:02d}",
            "fetched_at": fetched_at.isoformat(),
        }
    )


def cleanup_all_test_data(dynamodb_resource: Any, table_prefix: str) -> None:
    """全テストデータを削除する（各テーブルを全件スキャン → 削除）。"""
    table_bases = ["stations", "daily-temperature", "fetch-log"]
    for base in table_bases:
        table_name = f"{table_prefix}-{base}" if table_prefix else base
        table = dynamodb_resource.Table(table_name)
        # スキャンしてキーを収集
        items = []
        kwargs: dict[str, Any] = {}
        while True:
            response = table.scan(**kwargs)
            items.extend(response["Items"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        # バッチ削除
        if items:
            key_schema = table.key_schema
            key_names = [k["AttributeName"] for k in key_schema]
            with table.batch_writer() as batch:
                for item in items:
                    key = {k: item[k] for k in key_names}
                    batch.delete_item(Key=key)
