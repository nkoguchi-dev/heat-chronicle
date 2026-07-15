# Backend AGENTS.md

バックエンド（Python / FastAPI）の開発ガイドです。

## 開発コマンド

`backend/` ディレクトリで実行してください。

```bash
poetry install                                            # 依存関係インストール
poetry run uvicorn app.main:app --reload --port 8000      # 開発サーバー起動
poetry run pytest tests/ -v                               # テスト実行
poetry run pytest tests/test_jma_parser.py::test_name -v  # 単体テスト実行
```

### コード品質チェック（この順序で実行）

```bash
poetry run black .      # 1. フォーマット
poetry run isort .      # 2. import ソート
poetry run flake8 .     # 3. Lint
poetry run mypy .       # 4. 型チェック
poetry run pytest tests/ -v  # 5. テスト
```

## レイヤードアーキテクチャ

4 層構成を採用しています。依存方向は上から下への一方向のみ許可します。

| レイヤー | ディレクトリ | 責務 |
|----------|------------|------|
| Presentation | `presentation/api/` | FastAPI ルーター（HTTP ハンドリング） |
| Application | `application/` | ビジネスロジック（気象データ取得、キャッシュ判定） |
| Domain | `domain/` | ドメインモデル、純粋な業務ルール、I/O Port |
| Infrastructure | `infrastructure/` | DynamoDB アクセス、気象庁データ取得・解析 |

### レイヤー間の制約

- **Presentation → Application**: ルーターはサービス層のみを呼び出す
- **Presentation → Infrastructure**: 直接呼び出し禁止（必ず Application 層を経由する）
- **Application → Domain**: Application 層が import できるプロジェクト内レイヤーは Domain 層だけとする。Infrastructure / Presentation / DI の import を禁止する
- **Domain**: 他レイヤーに依存しない（純粋なドメインモデルと業務ルール）
- **Infrastructure → Domain**: Infrastructure 層は Domain 層の Repository / Port インターフェースを実装する。Application / Presentation / DI の import を禁止する
- **DI / Composition Root**: Application と Infrastructure の両方を import し、Domain のインターフェースに Infrastructure 実装を注入する唯一の場所とする

### モデルと DTO の境界

- **Domain Model**: Domain 層には外部フレームワークに依存しないドメインモデルを定義する。Pydantic の Request / Response / 永続化 DTO を置かない
- **Application Input**: Application 内部でドメイン処理に必要な入力には Domain Model を利用できる
- **Application Output**: Presentation 層へ返す値は、形が Domain Model と同じでもユースケース専用の Output DTO を dataclass で定義する。Output DTO のフィールドにも Domain Model を使い回さない
- **Presentation DTO**: HTTP の Request / Response は Presentation 層にエンドポイント専用の Pydantic Model として定義する
- **Infrastructure DTO**: DynamoDB、外部 API、ファイルなどの外部ペイロードは Infrastructure 層に用途専用の Pydantic Model として定義する
- **DTO の使い回し禁止**: レイヤー、ユースケース、エンドポイント、外部境界が異なる DTO は、フィールド構成が偶然同じでも共有しない
- **Application の明示的な変換**: Repository / Port から受け取った Domain Model は、Application Service の戻り値を作る境界でユースケース専用の Output DTO へ変換する
- **明示的な変換**: Presentation / Infrastructure の DTO は定義したレイヤーの外へ公開せず、境界で Domain Model または Application の型へ明示的に変換する
- **厳密な外部検証**: Presentation / Infrastructure の DTO は原則 `ConfigDict(strict=True, extra="forbid")` を設定し、暗黙の型変換と未知フィールドを許可しない
- **単純な HTTP パラメーター**: path / query の単純値は FastAPI の型付き引数で検証し、複合入力を扱う場合のみ専用 Request DTO を定義する
- **SDK の型を優先**: boto3 など公式の型定義がある設定値やレスポンス外枠には独自 DTO を重ねず、公式 stubs を利用する

Domain Model は `frozen=True` の dataclass を基本とし、Application 専用 DTO は標準 dataclass、外部境界 DTO は Pydantic Model を使用します。

Repository や外部データ取得など、Application が必要とする I/O は Domain 層に `Protocol` として定義し、Infrastructure 層で実装します。Application は具体実装を知らず、DI が実装を組み立てます。

### Application のファイル構成

- Application Service とユースケース固有の入出力は、`prefecture/`、`station/`、`temperature/` のような機能単位のディレクトリに配置する
- Application の Python ファイルを `application/` 直下へ直接追加しない
- 1つの Service に異なる機能のユースケースを混在させない
- Presentation 層から呼び出せる公開メソッドは、1つの Service クラスにつき1つまでとする。条件分岐を含む同一ユースケースは、引数を受け取る単一の公開メソッドにまとめる
- 複数の Service で同じ処理が必要な場合は `application/shared/` に共通処理を分離し、各 Service の単一の公開メソッドから呼び出す。Presentation 層から `application/shared/` を直接呼び出さない
- Service 内だけで使用する補助メソッドは `_` で始まる非公開メソッドにする

```text
application/
├── prefecture/
│   └── service.py
├── shared/              # 複数 Service の共通処理
├── station/
│   └── service.py
└── temperature/
    ├── service.py
    └── scrape_service.py
```

### Domain のファイル構成

- Domain Model、業務ルール、Repository / Port は、`station/` や `temperature/` のようなドメインリソース単位のディレクトリに配置する
- Domain の Python ファイルを `domain/` 直下へ直接追加しない
- リソースディレクトリ内では `model.py`、`repository.py`、`data_source.py` のように責務を表す snake_case のファイル名を使用する

```text
domain/
├── station/
│   ├── model.py       # 観測地点モデル
│   └── repository.py  # 観測地点 Repository Port
└── temperature/
    ├── model.py             # 日別気温モデル
    ├── repository.py        # 気温 Repository Port
    ├── data_source.py       # 気象データ取得 Port
    └── fetch_freshness.py   # 取得鮮度の業務ルール
```

### Presentation のファイル構成

- 1 つのファイルに定義できるエンドポイント（FastAPI のルートデコレータ）は 1 つだけとする
- Request / Response DTO は、それを使用するエンドポイントと同じファイルに定義する
- API リソースはエンドポイント数にかかわらず必ずリソース名のディレクトリを作成し、エンドポイントごとにファイルを分ける
- 各ファイル名は `get_temperature.py` のようにエンドポイントの操作を snake_case で表す
- リソースディレクトリの `__init__.py` は各ファイルの `router` を集約するだけとし、エンドポイント、DTO、ビジネスロジックを定義しない
- 複数エンドポイントで共通する Presentation 層の補助コードは `shared/` 配下に置き、エンドポイントファイルと混在させない

```text
presentation/api/temperature/
├── __init__.py          # router の集約のみ
├── get_temperature.py  # GET /{station_id} + 専用 Response DTO
└── fetch_month.py      # GET /{station_id}/fetch-month + 専用 Response DTO
```

## 主要パターン

- **リポジトリパターン**: Domain 層の `StationRepository` / `TemperatureRepository` Port を Infrastructure 層の DynamoDB Repository が実装する
- **依存性注入**: FastAPI の `Depends` を使用し、Presentation 層には Application Service を注入する
- **負荷を抑えたデータ取得**: フロントエンドが2秒以上の間隔で順次取得し、`JmaClient` は3回リトライ + 指数バックオフ

## API エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/api/prefectures` | 都道府県一覧 |
| GET | `/api/stations` | 観測地点一覧（`?prec_no=` でフィルタ可） |
| GET | `/api/temperature/{station_id}` | キャッシュ済み気温データ（`?start_year=&end_year=`） |
| GET | `/api/temperature/{station_id}/fetch-month` | 月別データ取得（`?year=&month=`） |

## コーディングスタイル

- **black**: line-length 88
- **isort**: profile "black"
- **flake8**: デフォルト設定
- **mypy**: strict モード

## エラーハンドリング方針

- 気象庁へのリクエスト失敗は `JmaClient` 内でリトライ後、例外を上位に伝播
- API レスポンスでは FastAPI の `HTTPException` を使用
- バリデーションエラーは Pydantic の自動バリデーションに委譲

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `DYNAMODB_ENDPOINT_URL` | DynamoDB Local の URL（ローカル開発時のみ） |
| `DYNAMODB_REGION` | AWS リージョン（デフォルト: `ap-northeast-1`） |
| `DYNAMODB_TABLE_PREFIX` | テーブル名のプレフィックス |
| `CORS_ALLOW_ORIGINS` | CORS 許可オリジン（デフォルト: `http://localhost:3000`） |
