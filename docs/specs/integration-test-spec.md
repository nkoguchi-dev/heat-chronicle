# heat-chronicle バックエンド Integration Test 仕様書

## 1. 概要

### 1.1 目的

heat-chronicle バックエンドにおいて、API エンドポイントに対する統合テスト（Integration Test）を導入する。統合テストでは FastAPI の `TestClient` を通じて実際に HTTP リクエストを送信し、レスポンスの内容および DynamoDB への副作用（データの書き込み・更新）を検証する。

### 1.2 既存テストとの棲み分け

| テスト種別 | ディレクトリ | 対象 | DB |
|-----------|-------------|------|-----|
| ユニットテスト | `tests/` | パーサー、ドメインロジック、リポジトリ単体 | moto モック |
| **統合テスト** | **`integration_tests/`** | **API エンドポイント経由の E2E フロー** | **DynamoDB Local（Docker）** |

### 1.3 参考プロジェクト

heat-chronicle のアーキテクチャ（DynamoDB + FastAPI + 気象庁スクレイパー）に最適化して設計する。

---

## 2. テスト基盤設計

### 2.1 ディレクトリ構成

```
backend/
├── integration_tests/
│   ├── __init__.py
│   ├── conftest.py                  # ルートフィクスチャ（DynamoDB セットアップ）
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── test_data.py             # テストデータ作成・クリーンアップ
│   │   └── mock_overrides.py        # 外部サービスモック（JmaClient 等）
│   └── api/
│       ├── __init__.py
│       ├── conftest.py              # API テスト用フィクスチャ（TestClient）
│       ├── test_health.py           # GET /health
│       ├── test_prefectures.py      # GET /api/prefectures
│       ├── test_stations.py         # GET /api/stations
│       └── test_temperature.py      # GET /api/temperature/{station_id} 関連
├── tests/                           # 既存ユニットテスト（変更なし）
└── pyproject.toml                   # testpaths に integration_tests を追加
```

### 2.2 DynamoDB Local を使用する理由

既存ユニットテストでは `moto` を使ったインメモリモックを使用しているが、統合テストでは以下の理由から DynamoDB Local を使用する。

- **実際の DynamoDB エンジンとの互換性**: GSI クエリ、ページネーション、Decimal 変換など、moto では再現しきれないエッジケースを検証できる
- **docker compose との整合性**: 開発環境と同じ DynamoDB Local コンテナを再利用できる
- **リアルな I/O パス**: boto3 の接続・タイムアウト設定を含めた実際のリクエスト経路を通る

### 2.3 テスト実行前提条件

```bash
# DynamoDB Local が起動していること
docker compose up dynamodb-local -d

# テスト実行
poetry run pytest integration_tests/ -v
```

---

## 3. フィクスチャ設計

### 3.1 ルート conftest.py（`integration_tests/conftest.py`）

セッションスコープで DynamoDB テーブルの作成・マイグレーションを行う。

```python
import pytest
import boto3
from app.config import Settings

TEST_TABLE_PREFIX = "test_"
TEST_DYNAMODB_ENDPOINT = "http://localhost:8000"


@pytest.fixture(scope="session")
def dynamodb_resource():
    """セッションスコープで DynamoDB Local への接続を確立する。"""
    resource = boto3.resource(
        "dynamodb",
        endpoint_url=TEST_DYNAMODB_ENDPOINT,
        region_name="ap-northeast-1",
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
    )
    yield resource


@pytest.fixture(scope="session", autouse=True)
def setup_tables(dynamodb_resource):
    """テスト用テーブルを作成し、マイグレーションを実行する。
    テーブル名にはプレフィックスを付与して本番データと分離する。
    """
    # テーブル作成 + seed_and_migrate をテスト用設定で実行
    # 全テスト完了後にテーブルを削除
    ...
    yield
    # teardown: テスト用テーブルを削除
    ...


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """テスト用の Settings を返す。"""
    return Settings(
        dynamodb_endpoint_url=TEST_DYNAMODB_ENDPOINT,
        dynamodb_region="ap-northeast-1",
        dynamodb_table_prefix=TEST_TABLE_PREFIX,
        cors_allow_origins="http://localhost:3000",
        scrape_interval_sec=0.0,  # テスト時はレート制限なし
    )
```

**設計ポイント**:
- テーブルにプレフィックス `test_` を付与し、開発環境のデータと分離する
- `scope="session"` でテストセッション全体で 1 回だけテーブルを作成する
- セッション終了時にテスト用テーブルを削除する

### 3.2 API テスト用 conftest.py（`integration_tests/api/conftest.py`）

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.di.container import get_station_repository, get_temperature_repository
from app.infrastructure.repositories.station_repository import StationRepository
from app.infrastructure.repositories.temperature_repository import TemperatureRepository


@pytest.fixture(scope="function")
async def client(dynamodb_resource, test_settings):
    """テストごとに新しい AsyncClient を作成する。
    DI をオーバーライドしてテスト用 DynamoDB を注入する。
    """
    def override_station_repo():
        return StationRepository(dynamodb_resource)

    def override_temp_repo():
        return TemperatureRepository(dynamodb_resource)

    app.dependency_overrides[get_station_repository] = override_station_repo
    app.dependency_overrides[get_temperature_repository] = override_temp_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
```

**設計ポイント**:
- `httpx.AsyncClient` + `ASGITransport` で非同期テストクライアントを構築する（参考プロジェクトのパターン）
- FastAPI の `dependency_overrides` でリポジトリの注入先をテスト用 DynamoDB に差し替える
- テストごとにクライアントを新規作成し、DI オーバーライドをクリアする

### 3.3 テストデータ管理（`integration_tests/fixtures/test_data.py`）

```python
from decimal import Decimal

# 基本テストデータ
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
    # ... 複数日分
]


async def insert_test_stations(dynamodb_resource, table_prefix: str) -> None:
    """テスト用の観測地点データを投入する。"""
    ...


async def insert_test_temperatures(dynamodb_resource, table_prefix: str) -> None:
    """テスト用の気温データを投入する。"""
    ...


async def cleanup_all_test_data(dynamodb_resource, table_prefix: str) -> None:
    """全テストデータを削除する。
    外部キー制約がないため順序は不問だが、
    テーブルごとに全件スキャン → バッチ削除で対応する。
    """
    ...
```

### 3.4 外部サービスモック（`integration_tests/fixtures/mock_overrides.py`）

参考プロジェクトの「デフォルトでエラーを投げる」パターンを採用する。

```python
class MockJmaClient:
    """JmaClient のモック。
    デフォルトではエラーを投げ、テストごとにレスポンスを設定する。
    """

    def __init__(self):
        self.responses: dict[tuple[int, int], str] = {}

    async def fetch_daily_page(
        self, prec_no: int, block_no: str,
        year: int, month: int, station_type: str,
    ) -> str:
        key = (year, month)
        if key in self.responses:
            return self.responses[key]
        raise RuntimeError(
            f"MockJmaClient: 未設定のリクエスト ({year}-{month:02d})"
        )

    async def close(self) -> None:
        pass

    def set_response(self, year: int, month: int, html: str) -> None:
        """テストから呼び出してモックレスポンスを設定する。"""
        self.responses[(year, month)] = html
```

**設計ポイント**:
- 気象庁への HTTP リクエスト（`JmaClient`）はモック化し、外部アクセスを遮断する
- デフォルトで `RuntimeError` を投げることで、意図しない外部呼び出しを即座に検知できる（参考プロジェクトのパターン）
- テストごとに `set_response()` でモック HTML を注入する

### 3.5 autouse フィクスチャによるデータクリーンアップ

```python
@pytest.fixture(autouse=True, scope="function")
async def clean_test_data(dynamodb_resource, test_settings):
    """各テスト前にテストデータをクリーンアップし、
    基本データ（stations）を再投入する。"""
    await cleanup_all_test_data(dynamodb_resource, test_settings.dynamodb_table_prefix)
    await insert_test_stations(dynamodb_resource, test_settings.dynamodb_table_prefix)
    yield
    # テスト後のクリーンアップは次のテストの前処理で行う
```

---

## 4. テストケース一覧

### 4.1 GET /health

| # | テスト名 | 説明 | 期待結果 |
|---|---------|------|---------|
| 1 | `test_health_check` | ヘルスチェックエンドポイントの正常応答 | 200, `{"status": "ok"}` |

### 4.2 GET /api/prefectures

| # | テスト名 | 説明 | 期待結果 |
|---|---------|------|---------|
| 1 | `test_get_prefectures_returns_all` | 全都道府県が返却される | 200, 48 件（47 都道府県 + 南極） |
| 2 | `test_get_prefectures_structure` | レスポンスの構造が正しい | 各要素に `prec_no`（int）と `name`（str）が含まれる |
| 3 | `test_get_prefectures_includes_tokyo` | 東京が含まれている | `prec_no=44, name="東京都"` が存在する |

### 4.3 GET /api/stations

| # | テスト名 | 説明 | 期待結果 |
|---|---------|------|---------|
| 1 | `test_get_all_stations` | 全観測地点一覧を取得する | 200, テストデータの全地点が返却される |
| 2 | `test_get_stations_by_prec_no` | `?prec_no=44` で東京の地点のみ | 200, `prec_no=44` の地点のみ返却 |
| 3 | `test_get_stations_by_prec_no_empty` | 存在しない `prec_no` を指定 | 200, 空配列 `[]` |
| 4 | `test_get_stations_response_structure` | レスポンス構造の検証 | 各要素に `id`, `station_name`, `prec_no`, `block_no`, `station_type` 等が含まれる |
| 5 | `test_get_stations_includes_earliest_year` | `earliest_year` フィールドが含まれる | 値が int または null |

### 4.4 GET /api/temperature/{station_id}

| # | テスト名 | 説明 | 期待結果 |
|---|---------|------|---------|
| 1 | `test_get_temperature_success` | キャッシュ済みデータの取得 | 200, `metadata` + `data` が返却される |
| 2 | `test_get_temperature_with_end_year` | `?end_year=2023` を指定 | 200, `metadata.end_year == 2023` |
| 3 | `test_get_temperature_station_not_found` | 存在しない `station_id` を指定 | 404, `detail` にエラーメッセージ |
| 4 | `test_get_temperature_metadata_structure` | メタデータの構造検証 | `station_id`, `station_name`, `start_year`, `end_year`, `total_records`, `fetched_months`, `fetching_required`, `has_older_data`, `next_end_year` |
| 5 | `test_get_temperature_empty_data` | データが存在しない地点 | 200, `data` が空配列, `fetching_required == True` |
| 6 | `test_get_temperature_fetching_required_when_unfetched` | 未取得月がある場合 | `fetching_required == True` |
| 7 | `test_get_temperature_has_older_data` | 50 年チャンクより古いデータがある場合 | `has_older_data == True`, `next_end_year` が設定される |

### 4.5 GET /api/temperature/{station_id}/fetch-month

| # | テスト名 | 説明 | 期待結果 |
|---|---------|------|---------|
| 1 | `test_fetch_month_success` | 新規月のスクレイピング成功 | 200, `records` に日別データ, DB に気温データが書き込まれる |
| 2 | `test_fetch_month_cached` | キャッシュ済み月の再取得 | 200, JmaClient が呼び出されない（DB からデータ返却） |
| 3 | `test_fetch_month_station_not_found` | 存在しない `station_id` | 404 |
| 4 | `test_fetch_month_invalid_month` | `month=13` を指定 | 400, `"month must be 1-12"` |
| 5 | `test_fetch_month_invalid_month_zero` | `month=0` を指定 | 400 |
| 6 | `test_fetch_month_future_month` | 未来の年月を指定 | 200, `records` が空配列 |
| 7 | `test_fetch_month_db_side_effects` | スクレイピング後の DB 検証 | `daily-temperature` テーブルにレコードが存在, `fetch-log` テーブルにログが記録される |
| 8 | `test_fetch_month_response_structure` | レスポンス構造の検証 | `year`, `month`, `records` を含み、各レコードに `date`, `max_temp`, `min_temp`, `avg_temp` |

---

## 5. テストパターン詳細

### 5.1 基本的な API テストパターン

参考プロジェクトの AAA（Arrange-Act-Assert）パターンに従う。

```python
@pytest.mark.asyncio
async def test_get_stations_by_prec_no(client: AsyncClient) -> None:
    """prec_no でフィルタした観測地点一覧を取得できる。"""
    # Act
    response = await client.get("/api/stations/", params={"prec_no": 44})

    # Assert - HTTP レスポンス
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Assert - 全件が指定 prec_no
    for station in data:
        assert station["prec_no"] == 44
```

### 5.2 DB 副作用検証パターン

スクレイピング API の場合、レスポンスに加えて DynamoDB の状態も検証する。

```python
@pytest.mark.asyncio
async def test_fetch_month_db_side_effects(
    client: AsyncClient,
    dynamodb_resource,
    test_settings: Settings,
    mock_jma_client: MockJmaClient,
) -> None:
    """fetch-month 後に DB にデータが書き込まれることを検証する。"""
    # Arrange - モック HTML を設定
    mock_jma_client.set_response(2024, 8, SAMPLE_JMA_HTML)

    # Act
    response = await client.get(
        "/api/temperature/47662/fetch-month",
        params={"year": 2024, "month": 8},
    )

    # Assert - レスポンス
    assert response.status_code == 200
    records = response.json()["records"]
    assert len(records) > 0

    # Assert - daily-temperature テーブル
    table = dynamodb_resource.Table(f"{test_settings.dynamodb_table_prefix}daily-temperature")
    result = table.query(
        KeyConditionExpression="station_id = :sid AND #d BETWEEN :start AND :end",
        ExpressionAttributeNames={"#d": "date"},
        ExpressionAttributeValues={
            ":sid": 47662,
            ":start": "2024-08-01",
            ":end": "2024-08-31",
        },
    )
    assert result["Count"] > 0

    # Assert - fetch-log テーブル
    log_table = dynamodb_resource.Table(f"{test_settings.dynamodb_table_prefix}fetch-log")
    log_result = log_table.get_item(
        Key={"station_id": 47662, "year_month": "2024-08"}
    )
    assert "Item" in log_result
    assert "fetched_at" in log_result["Item"]
```

### 5.3 外部サービスモック注入パターン

`ScrapeService` 内で `JmaClient` を直接インスタンス化しているため、`unittest.mock.patch` でモックを注入する。

```python
@pytest.fixture
def mock_jma_client():
    """JmaClient のモックインスタンスを返す。"""
    return MockJmaClient()


@pytest.fixture(autouse=True)
def patch_jma_client(mock_jma_client):
    """ScrapeService 内の JmaClient をモックに差し替える。"""
    with patch(
        "app.application.scrape_service.JmaClient",
        return_value=mock_jma_client,
    ):
        yield
```

---

## 6. pyproject.toml の変更

### 6.1 テストパス設定

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests", "integration_tests"]
pythonpath = ["."]
```

> **注**: 既存の `testpaths` に `integration_tests` が設定済みであることを確認する。

### 6.2 追加依存パッケージ

```toml
[tool.poetry.group.dev.dependencies]
# 既存
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
moto = {extras = ["dynamodb"], version = "^5.0.0"}

# 追加
httpx = "^0.28.0"  # AsyncClient（既にランタイム依存に含まれている場合は不要）
```

> **注**: `httpx` は既にランタイム依存に含まれているため、追加インストールは不要な可能性がある。

### 6.3 テスト実行コマンド

```bash
# ユニットテストのみ
poetry run pytest tests/ -v

# 統合テストのみ
poetry run pytest integration_tests/ -v

# 全テスト
poetry run pytest -v

# 特定テストの実行
poetry run pytest integration_tests/api/test_temperature.py::test_fetch_month_success -v
```

---

## 7. GitHub Actions CI ワークフローの変更

### 7.1 現状の CI 構成

現在の `.github/workflows/ci-backend.yml` は以下の構成になっている。

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - Checkout → Setup Python → Install Poetry → Cache → Install dependencies
      - black --check → isort --check-only → flake8 → mypy
      - poetry run pytest -v  # tests/ のみ（integration_tests/ は存在しない）
```

`pyproject.toml` の `testpaths` に `integration_tests` が含まれているため、`poetry run pytest -v` を実行すると統合テストも対象になる。しかし、DynamoDB Local が起動していないと統合テストは失敗する。

### 7.2 変更方針

ジョブを **2 つに分離** する。

| ジョブ | 内容 | DynamoDB Local |
|-------|------|----------------|
| `lint-and-unit-test` | 静的解析 + ユニットテスト | 不要 |
| `integration-test` | 統合テスト | 必要（`services` で起動） |

**分離する理由**:
- ユニットテストは外部依存なしで高速に実行でき、lint エラーも早期に検出したい
- 統合テストは DynamoDB Local の起動に数秒かかるため、独立ジョブにすることで lint 失敗時に無駄なコンテナ起動を避けられる
- ジョブ間の依存（`needs`）を設定することで、ユニットテストが通らなければ統合テストをスキップできる

### 7.3 変更後のワークフロー定義

```yaml
name: CI Backend

on:
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]
    paths:
      - backend/**
      - .github/workflows/ci-backend.yml

jobs:
  # ────────────────────────────────────────────
  # Job 1: 静的解析 + ユニットテスト（既存相当）
  # ────────────────────────────────────────────
  lint-and-unit-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Poetry
        run: pip install poetry

      - name: Configure Poetry
        run: poetry config virtualenvs.in-project true

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: backend/.venv
          key: ${{ runner.os }}-poetry-${{ hashFiles('backend/poetry.lock') }}
          restore-keys: |
            ${{ runner.os }}-poetry-

      - name: Install dependencies
        working-directory: backend
        run: poetry install --no-interaction

      - name: Check formatting (black)
        working-directory: backend
        run: poetry run black --check .

      - name: Check import order (isort)
        working-directory: backend
        run: poetry run isort --check-only .

      - name: Lint (flake8)
        working-directory: backend
        run: poetry run flake8 .

      - name: Type check (mypy)
        working-directory: backend
        run: poetry run mypy .

      - name: Run unit tests
        working-directory: backend
        run: poetry run pytest tests/ -v

  # ────────────────────────────────────────────
  # Job 2: 統合テスト（DynamoDB Local 必要）
  # ────────────────────────────────────────────
  integration-test:
    runs-on: ubuntu-latest
    needs: lint-and-unit-test  # ユニットテスト通過後に実行

    services:
      dynamodb-local:
        image: amazon/dynamodb-local:latest
        ports:
          - 8000:8000
        options: >-
          --health-cmd "curl -s http://localhost:8000/shell/ || exit 1"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Poetry
        run: pip install poetry

      - name: Configure Poetry
        run: poetry config virtualenvs.in-project true

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: backend/.venv
          key: ${{ runner.os }}-poetry-${{ hashFiles('backend/poetry.lock') }}
          restore-keys: |
            ${{ runner.os }}-poetry-

      - name: Install dependencies
        working-directory: backend
        run: poetry install --no-interaction

      - name: Wait for DynamoDB Local
        run: |
          for i in $(seq 1 10); do
            curl -s http://localhost:8000/shell/ > /dev/null && break
            echo "Waiting for DynamoDB Local... ($i)"
            sleep 2
          done

      - name: Run integration tests
        working-directory: backend
        run: poetry run pytest integration_tests/ -v
        env:
          DYNAMODB_ENDPOINT_URL: http://localhost:8000
          DYNAMODB_TABLE_PREFIX: test_
```

### 7.4 設計上のポイント

**`services` ブロックについて**:
- GitHub Actions の `services` はジョブ開始時に Docker コンテナを自動起動し、ジョブ終了時に自動破棄する
- `ports` でホストの `8000` にマッピングすることで、テストコードから `http://localhost:8000` でアクセスできる
- `options` でヘルスチェックを設定し、コンテナが応答可能になってからステップを実行する

**`needs: lint-and-unit-test` について**:
- ユニットテスト・lint が失敗した場合、統合テストジョブはスキップされる
- DynamoDB Local の起動コストを無駄にしない

**`Wait for DynamoDB Local` ステップについて**:
- `services` のヘルスチェックは「コンテナが起動した」ことを保証するが、実際にリクエストを受け付け可能になるまでのラグをカバーするために追加する
- 最大 20 秒（2 秒 × 10 回）待機する

**環境変数について**:
- `DYNAMODB_ENDPOINT_URL` と `DYNAMODB_TABLE_PREFIX` をステップの `env` で渡す
- テスト用 conftest.py ではこの環境変数を読み取るか、またはハードコードされたテスト用デフォルト値を使用する
- 本番用の AWS 認証情報は不要（DynamoDB Local はダミー認証で動作する）

**Poetry キャッシュの共有**:
- 両ジョブで同じキャッシュキーを使用するため、2 つ目のジョブでは依存関係のインストールがキャッシュヒットにより高速化される

---

## 8. 設計上の判断事項

### 8.1 参考プロジェクトとの差分

| 項目 | 参考プロジェクト | heat-chronicle | 理由 |
|------|-----------------|----------------|------|
| DB | PostgreSQL（testcontainers） | DynamoDB Local（Docker） | プロジェクトの DB が DynamoDB のため |
| ORM | SQLAlchemy async | boto3 (sync/async) | DynamoDB には ORM がないため |
| 認証 | Auth0 モック + marker | なし | 認証機能が未実装のため |
| TestClient | `httpx.AsyncClient` | `httpx.AsyncClient` | 同一パターンを踏襲 |
| 外部 API モック | DI オーバーライド | `unittest.mock.patch` | JmaClient が DI 経由でないため |
| データクリーンアップ | FK 順序で DELETE | テーブル全件スキャン + 削除 | DynamoDB に FK 制約がないため |

### 8.2 JmaClient のモック方式

`ScrapeService` 内で `JmaClient()` を直接インスタンス化しているため、FastAPI の `dependency_overrides` では差し替えられない。`unittest.mock.patch` でクラス自体をモックする。

将来的に `JmaClient` を DI コンテナ経由で注入する設計に変更すれば、`dependency_overrides` による差し替えが可能になるが、本仕様では現状のコードに対する最小限の変更で対応する。

### 8.3 テストデータの冪等性

各テストは `autouse` フィクスチャでデータをクリーンアップし、基本データを再投入する。これにより、テストの実行順序に依存しない冪等なテストを実現する。

---

## 9. 実装優先度

| 優先度 | 対象 | 理由 |
|-------|------|------|
| **P0** | テスト基盤（conftest, fixtures, mock） | 全テストの前提条件 |
| **P1** | `/api/temperature/{station_id}/fetch-month` | 副作用（DB 書き込み）を伴う最も複雑な API |
| **P2** | `/api/temperature/{station_id}` | キャッシュ判定ロジックを含む API |
| **P3** | `/api/stations` | DB 読み取り + フィルタリング |
| **P4** | `/api/prefectures`, `/health` | 純粋関数的で副作用なし |
