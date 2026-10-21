# Backend AGENTS.md

バックエンド（Python / FastAPI）の開発ガイドです。

## 開発コマンド

rootのMake targetは[ローカル開発契約](../docs/LOCAL_DEVELOPMENT.md)を正本とします。setup/dev/stop/check/browser-smokeへ集約し、以下の個別コマンドもデバッグ用に維持します。

`backend/` ディレクトリで実行してください。

```bash
uv sync --locked                                            # 依存関係インストール
uv run --locked uvicorn app.main:app --reload --port 8000      # 開発サーバー起動
uv run --locked pytest tests/ -v                               # テスト実行
uv run --locked pytest tests/test_jma_parser.py::test_name -v  # 単体テスト実行
```

### コード品質チェック（この順序で実行）

```bash
uv run --locked black .      # 1. フォーマット
uv run --locked isort .      # 2. import ソート
uv run --locked flake8 .     # 3. Lint
uv run --locked mypy .       # 4. 型チェック
uv run --locked pytest tests/ -v  # 5. テスト
```

## Port／Adapterアーキテクチャ

目標構成と段階移行の正本は[バックエンド設計](../docs/BACKEND_ARCHITECTURE.md)です。
Issue #153〜#159で全API経路を移行しました。ApplicationがInbound/Outbound Portを所有し、Domainはモデルと純粋な規則だけを持ちます。
移行例外はありません。`tests/layer_rules.py`がimport境界とDI外の具象生成を検査します。

| 役割 | ディレクトリ | 責務 |
|------|-------------|------|
| Inbound Adapter | `presentation/api/` | HTTP検証、Inbound Port呼び出し、専用Responseへの変換 |
| Application | `application/` | Inbound／Outbound Port、入出力、Use Case、取得手順 |
| Domain | `domain/` | 外部I/Oを持たないモデル、純粋な業務規則 |
| Outbound Adapter | `infrastructure/` | DynamoDB、気象庁、実時計と外部DTO変換 |
| Composition Root | `di/` | Portと具象の接続、外部client生成・終了の配線 |

### レイヤー間の制約

- **Presentation → Application Inbound Port**: endpointは`application/<feature>/ports/inbound/`の契約だけに依存する。Use Case具象、Outbound Port、Domain、Infrastructure、DIをimportしない。
- **Application → Domain**: Application内とDomainだけをimportできる。FastAPI、Pydantic、boto3、具体Adapter、Presentation、DI、設定への依存を禁止する。
- **Domain**: 標準ライブラリとDomain内だけに依存する。外部I/O Protocol、Application、framework、実時計参照を置かない。
- **Infrastructure → Application Outbound Port / Domain**: Outbound PortとDomainモデル・規則を利用できる。Inbound Port、Use Case具象、Presentation、DIへの依存を禁止する。
- **DI / Composition Root**: Inbound Port、Use Case、Outbound Adapterの具象を接続する唯一の場所。mainとLambda handlerはDIの初期化・登録を呼び、router、middleware、起動終了を配線する。
- FastAPIの`Depends`はPresentation内のPort型付き依存関数を指し、Composition Rootがproviderを登録する。endpointからDIの具象Use Case aliasをimportしない。
- import境界テストは絶対／相対importの違反と、DI外のUse Case/Adapter生成を検出する。例外を追加して迂回しない。

### モデルと DTO の境界

- **Domain Model**: Domain 層には外部フレームワークに依存しないドメインモデルを定義する。Pydantic の Request / Response / 永続化 DTO を置かない
- **Application Input**: Application 内部でドメイン処理に必要な入力には Domain Model を利用できる
- **Application Output**: Presentation 層へ返す値は、形が Domain Model と同じでもユースケース専用の Output DTO を dataclass で定義する。Output DTO のフィールドにも Domain Model を使い回さない
- **Presentation DTO**: HTTP の Request / Response は Presentation 層にエンドポイント専用の Pydantic Model として定義する
- **Infrastructure DTO**: DynamoDB、外部 API、ファイルなどの外部ペイロードは Infrastructure 層に用途専用の Pydantic Model として定義する
- **DTO の使い回し禁止**: レイヤー、ユースケース、エンドポイント、外部境界が異なる DTO は、フィールド構成が偶然同じでも共有しない
- **Application の明示的な変換**: Repository / Port から受け取った Domain Model は、UseCase の戻り値を作る境界でユースケース専用の Output DTO へ変換する
- **明示的な変換**: Presentation / Infrastructure の DTO は定義したレイヤーの外へ公開せず、境界で Domain Model または Application の型へ明示的に変換する
- **厳密な外部検証**: Presentation / Infrastructure の DTO は原則 `ConfigDict(strict=True, extra="forbid")` を設定し、暗黙の型変換と未知フィールドを許可しない
- **単純な HTTP パラメーター**: path / query の単純値は FastAPI の型付き引数で検証し、複合入力を扱う場合のみ専用 Request DTO を定義する
- **SDK の型を優先**: boto3 など公式の型定義がある設定値やレスポンス外枠には独自 DTO を重ねず、公式 stubs を利用する

Domain Model は `frozen=True` の dataclass を基本とし、Application 専用 DTO は標準 dataclass、外部境界 DTO は Pydantic Model を使用します。

Applicationが必要とする外部I/Oは`application/<feature>/ports/outbound/`の`Protocol`として所有し、Infrastructureが実装します。Inbound Portと公開する入出力は`ports/inbound/`へ置き、Use Case具象から分離します。詳細な配置と移行中の例外は[バックエンド設計](../docs/BACKEND_ARCHITECTURE.md)を参照してください。

### Application のファイル構成

- UseCase クラスとPort・ユースケース固有の入出力は、`prefecture/`、`station/`、`temperature/` のような機能単位のディレクトリに配置する
- Application の Python ファイルを `application/` 直下へ直接追加しない
- 1つのユースケースにつき1つの UseCase クラスを作成し、異なるユースケースを1つのクラスに混在させない
- UseCase クラスは `ListStationUseCase` のように操作名を含めて `UseCase` を接尾辞とし、ファイル名は `list_station_use_case.py` のように操作を表す snake_case とする
- Presentation 層から呼び出せる公開メソッドは、1つの UseCase クラスにつき1つまでとする。条件分岐を含む同一ユースケースは、引数を受け取る単一の公開メソッドにまとめる
- 複数の UseCase から呼び出される処理は `application/shared/` に Service クラスとして分離し、各 UseCase から呼び出す。Presentation 層から `application/shared/` を直接呼び出さない
- UseCase または Service 内だけで使用する補助メソッドは `_` で始まる非公開メソッドにする

```text
application/
├── prefecture/
│   ├── ports/inbound/list_prefecture.py  # Portと専用Output
│   └── list_prefecture_use_case.py
├── shared/
│   └── ports/outbound/clock.py         # 実時計の契約
├── station/
│   ├── ports/inbound/list_station.py    # Port・専用Output・未検出例外
│   ├── ports/outbound/repository.py     # StationRepository
│   └── list_station_use_case.py
└── temperature/
    ├── ports/inbound/                  # Port・専用Output・例外
    ├── ports/outbound/                 # Repository・Data Source・Guard
    ├── get_temperature_use_case.py
    └── fetch_month_use_case.py
```

### Domain のファイル構成

Domainに外部I/O Protocolを置かず、ApplicationのOutbound Portとして所有します。

- Domain Model、純粋な業務ルールは、`station/` や `temperature/` のようなドメインリソース単位のディレクトリに配置する
- Domain の Python ファイルを `domain/` 直下へ直接追加しない
- リソースディレクトリ内では `model.py`、`fetch_freshness.py`、`input_policy.py` のように責務を表す snake_case のファイル名を使用する

```text
domain/
├── station/
│   └── model.py
└── temperature/
    ├── model.py
    ├── fetch_freshness.py
    └── input_policy.py
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

- **リポジトリパターン**: Application所有の `StationRepository` / `TemperatureRepository` Outbound Port を Infrastructure 層の DynamoDB Repository が実装する
- **依存性注入**: FastAPI の `Depends` を使用し、Presentation層にはInbound Port型でUse Case実装を注入する
- **負荷を抑えたデータ取得**: フロントエンドが2秒以上の間隔で順次取得し、サーバーは共有leaseで上流を直列化する。`JmaClient`は最大3試行、試行間隔2秒以上、1試行8秒。詳細は`docs/API_PROTECTION.md`を参照

## API エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/api/prefectures` | 都道府県一覧 |
| GET | `/api/stations` | 観測地点一覧（`?prec_no=` でフィルタ可） |
| GET | `/api/temperature/{station_id}` | キャッシュ済み気温データ（`?end_year=`、最大50年） |
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

## 時刻の取得

- 現在時刻と経過時間は`Clock` Outbound Portを通して取得し、DIから注入する。`application/shared/ports/outbound/clock.py`が契約を所有する。
- `datetime.now()`・`date.today()`・`time.time()`・`time.monotonic()`の実時計参照はInfrastructureの`SystemClock`へ集約する。日時値の構築・変換・比較は各層で行ってよい。
- `Clock.now()`はtimezone-awareなUTC日時を返す。観測年月はDomainの純粋な変換で日本時間へ揃える。共有lease期限には壁時計、実行中の取得予算には単調増加時計を使い、混同しない。
- テストでは固定時計を注入し、時刻取得関数のpatchで時計依存を隠さない。

## 型付きの失敗結果

Issue #245で[結果契約](../docs/BACKEND_ARCHITECTURE.md)を定義し、#246〜#251で段階移行します。想定内失敗は原則frozen dataclassとUnionで返し、呼び出し側はmatchで明示変換します。Outbound/Inbound/HTTPで失敗型を共有しません。
網羅分岐はassert_neverとmypy strictで確認し、HTTPは想定内失敗でResponseを返します。外部SDK/clientの必要な例外捕捉、起動時の構成エラー、想定外500、asyncio timeout/cancel cleanupは維持します。全Exception/RuntimeErrorを業務結果へ丸めません。
