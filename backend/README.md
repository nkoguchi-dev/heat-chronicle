# backend

Python / FastAPI によるバックエンド API サーバーです。気象庁が公開している過去の気象観測データを取得・解析し、DynamoDB にキャッシュしたうえで REST API として提供します。

## 技術構成

- **Python 3.14** / **FastAPI**
- **boto3** — DynamoDB アクセス
- **httpx + BeautifulSoup4 (lxml)** — 気象庁 HTML ページからの観測データ取得・解析
- **Mangum** — AWS Lambda 上での FastAPI 実行アダプタ
- **uv** — Python・仮想環境・locked依存の管理

## ディレクトリ構成

```
backend/
├── app/
│   ├── main.py                      … FastAPI アプリケーション
│   ├── handler.py                   … Lambda ハンドラ（Mangum）
│   ├── config.py                    … 環境変数ベースの設定
│   ├── presentation/api/            … API ルーター（HTTP ハンドラ）
│   │   ├── health/get_health.py     … ヘルスチェック
│   │   ├── hello/get_hello.py       … Hello API
│   │   ├── prefectures/             … 都道府県一覧
│   │   │   └── get_prefectures.py
│   │   ├── shared/                 … Presentation 共通コード
│   │   │   └── internal_server_error.py
│   │   ├── stations/                … 観測地点一覧
│   │   │   └── get_stations.py
│   │   └── temperature/             … 気温データ取得
│   │       ├── fetch_month.py       … 月別データ取得
│   │       └── get_temperature.py   … キャッシュ済みデータ取得
│   ├── application/                 … ユースケース層
│   │   ├── prefecture/
│   │   │   └── list_prefecture_use_case.py … 都道府県一覧の取得
│   │   ├── station/
│   │   │   └── list_station_use_case.py   … 観測地点一覧の取得
│   │   └── temperature/
│   │       ├── fetch_month_use_case.py     … 気象庁からの月別データ取得
│   │       └── get_temperature_use_case.py … キャッシュ済みデータのクエリ
│   ├── domain/                      … ドメインモデル、業務ルール、I/O Port
│   │   ├── station/                … 観測地点ドメイン
│   │   │   ├── model.py            … 観測地点モデル
│   │   │   └── repository.py       … 観測地点 Repository Port
│   │   └── temperature/            … 気温ドメイン
│   │       ├── data_source.py      … 気象データ取得 Port
│   │       ├── fetch_freshness.py  … 取得鮮度の業務ルール
│   │       ├── model.py            … 日別気温モデル
│   │       └── repository.py       … 気温 Repository Port
│   └── infrastructure/              … DB / 外部サービス
│       ├── database.py              … DynamoDB クライアント初期化
│       ├── dto/                     … 外部ペイロードの Pydantic DTO
│       ├── init_tables.py           … テーブル自動作成
│       ├── seed.py                  … 初期データ投入
│       ├── repositories/            … リポジトリパターン
│       │   ├── station_repository.py
│       │   └── temperature_repository.py
│       └── scraper/                 … 気象庁データの取得・解析
│           ├── jma_client.py        … HTTP クライアント（リトライ付き）
│           ├── jma_parser.py        … HTML パーサー
│           └── jma_temperature_data_source.py … 気象データ取得Port実装
├── data/                            … シードデータ（地点マスタ CSV 等）
├── tests/                           … ユニットテスト
├── pyproject.toml                   … PEP 621/735と品質ツールの設定
├── Dockerfile                       … ローカル開発用
└── Dockerfile.prod                  … 本番用（Lambda コンテナ）
```

コーディング規約・開発コマンド・アーキテクチャの詳細は [AGENTS.md](./AGENTS.md) を参照してください。

## 気象庁データ取得仕様

気象庁への負荷を抑えるため、以下のルールに従ってデータを取得します。

- リクエスト間隔: フロントエンドから最低 2 秒間隔で順次呼び出し
- リトライ: 最大 3 回 + 指数バックオフ
- 取得単位: 1 リクエスト = 1 ヶ月分
- キャッシュ: `fetch-log` テーブルで取得済み年月を管理し、再取得を防止

## 開発環境の移行契約

Python・ホスト・DB・Docker・CIの責務と段階的な移行順は[バックエンド開発環境の契約](../docs/BACKEND_DEVELOPMENT.md)を参照してください。

## ホストの依存環境

uv 0.12.0を導入し、backendをカレントとして実行します。

```sh
uv sync --locked
uv run --locked python --version
uv run --locked black --check .
uv run --locked isort --check-only .
uv run --locked flake8 .
uv run --locked mypy .
uv run --locked pytest tests/
```

.python-versionは3.14を選択し、パッチ版は固定しません。runtime依存とdev groupは標準pyproject、解決版はuv.lockが正本です。
ホスト・CI・両imageは標準metadataとuv.lockを使用し、Poetry互換資源はありません。
既存ローカルDBのデータは変更しません。

## ホストFastAPIとDynamoDB Local

リポジトリrootで`docker compose up -d --wait dynamodb-local`を実行します。
既存database/dataを維持するため、volumeやデータを削除する停止コマンドは使いません。
backendをカレントに、初回だけ`.env.example`を`.env.local`へコピーします。既存ファイルは上書きせず差分を確認してください。

```sh
uv sync --locked
uv run --locked uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# 別ターミナルからhealth、都道府県、地点APIを確認する。
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/api/prefectures
curl --fail 'http://127.0.0.1:8000/api/stations?prec_no=44'
```

起動時lifespanがtableを初期化し、既存のstation seed/migrationを実行します。
ホストは127.0.0.1:8001、独立したimage検証では専用networkのdynamodb-local:8000を明示します。
ComposeはDynamoDB Localだけを提供し、backend/frontendはホスト上で実行します。
本番はendpointを設定せずSDKの通常解決を維持します。

integrationは専用のtestまたはtest-で始まるprefixを環境変数で明示します。
loopback HTTP endpointとportがない場合は、client生成・データcleanupより前に失敗させます。
通常のlocal prefixを使わないでください。unitはsocket接続自体を禁止し、moto/HTTP mockだけを使います。

```sh
DYNAMODB_ENDPOINT_URL=http://127.0.0.1:8001 DYNAMODB_TABLE_PREFIX=test-host uv run --locked pytest integration_tests/
```

終了時はFastAPIをCtrl-Cで止め、rootで`docker compose stop dynamodb-local`を実行します。
ローカルデータはそのまま保持されます。外部気象庁の取得は通常の接続確認には不要です。

## Linux imageの検証

開発用は`docker build -f backend/Dockerfile -t heat-backend-dev backend`、Lambda用は
`docker buildx build --platform linux/amd64 --pull --no-cache-filter base --provenance=false --load -f backend/Dockerfile.prod -t heat-backend-lambda backend`
で構築します。両方ともuv 0.12.0の固定digestとuv.lockを使います。開発用の環境は/opt/venvに置き、ソースbind mountで上書きしません。
開発用imageからDBへは明示したcontainer内endpointを指定し、health・主要APIを確認します。
Lambdaはruntimeだけをtask rootへ導入し、uvや開発依存は最終imageへコピーしません。
rootのtools/containers/smoke.pyを最終image内で実行して、AWS接続なしのhandlerを確認します。
imageのbuild・検査は本番配備を意味しません。

rootで`sh tools/run-backend-development-smoke.sh`を実行すると、専用のin-memory DB・networkで開発imageを検証し、自分の一時containerを終了時に削除します。既存DBのvolumeには触れません。

## CIと依存更新

backendのPR/main CIは固定版setup-uv Actionとuv 0.12.0でPython 3.14を選択し、locked環境から既存の静的検査・unit/integrationを実行します。
required check名とRulesetを維持し、開発imageの専用DB smokeも実行します。
Lambda imageは既存Container Securityでbuild・隔離handler・脆弱性/秘密検査を継続します。
Dependabotのbackendはuv ecosystemへ切り替えます。CI成功や候補buildを本番配備と扱いません。

専用portで確認する場合は、frontendのoriginをCORS_ALLOW_ORIGINSへ明示し、frontendのHEAT_CHRONICLE_API_PROXY_TARGETをホストAPIのportへ合わせます。既定手順はfrontend localhost:3000、API 127.0.0.1:8000です。

移行完了時の新worktree・host/DB/frontend・両image・CIの確認範囲は[結合確認](../docs/BACKEND_VERIFICATION.md)を参照してください。
