# backend

Python / FastAPI によるバックエンド API サーバーです。気象庁が公開している過去の気象観測データを取得・解析し、DynamoDB にキャッシュしたうえで REST API として提供します。

## 技術構成

- **Python 3.14** / **FastAPI**
- **boto3** — DynamoDB アクセス
- **httpx + BeautifulSoup4 (lxml)** — 気象庁 HTML ページからの観測データ取得・解析
- **Mangum** — AWS Lambda 上での FastAPI 実行アダプタ
- **Poetry** — 依存関係管理

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
│   ├── application/                 … サービス層
│   │   ├── prefecture_service.py    … 都道府県一覧の取得
│   │   ├── scrape_service.py        … 気象庁からの月別データ取得
│   │   └── temperature_service.py   … キャッシュ済みデータのクエリ
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
├── pyproject.toml                   … Poetry 設定
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
