# backend

Python / FastAPI によるバックエンド API サーバーです。気象庁の公開ページからデータをスクレイピングし、DynamoDB にキャッシュしたうえで REST API として提供します。

## 技術構成

- **Python 3.12** / **FastAPI**
- **boto3** — DynamoDB アクセス
- **httpx + BeautifulSoup4 (lxml)** — 気象庁 HTML ページのスクレイピング
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
│   │   ├── hello.py                 … ヘルスチェック
│   │   ├── prefectures.py           … 都道府県一覧
│   │   ├── stations.py              … 観測地点一覧
│   │   └── temperature.py           … 気温データ取得
│   ├── application/                 … サービス層
│   │   ├── scrape_service.py        … 気象庁からの月別データ取得
│   │   └── temperature_service.py   … キャッシュ済みデータのクエリ
│   ├── domain/                      … Pydantic レスポンススキーマ
│   │   ├── prefectures.py           … 都道府県マスタ
│   │   └── schemas.py               … API レスポンス型定義
│   └── infrastructure/              … DB / 外部サービス
│       ├── database.py              … DynamoDB クライアント初期化
│       ├── init_tables.py           … テーブル自動作成
│       ├── seed.py                  … 初期データ投入
│       ├── repositories/            … リポジトリパターン
│       │   ├── station_repository.py
│       │   └── temperature_repository.py
│       └── scraper/                 … 気象庁スクレイパー
│           ├── jma_client.py        … HTTP クライアント（レート制限付き）
│           └── jma_parser.py        … HTML パーサー
├── data/                            … シードデータ（地点マスタ CSV 等）
├── tests/                           … ユニットテスト
├── pyproject.toml                   … Poetry 設定
├── Dockerfile                       … ローカル開発用
└── Dockerfile.prod                  … 本番用（Lambda コンテナ）
```

コーディング規約・開発コマンド・アーキテクチャの詳細は [CLAUDE.md](./CLAUDE.md) を参照してください。

## スクレイピング仕様

気象庁への負荷を抑えるため、以下のルールに従ってデータを取得します。

- リクエスト間隔: 最低 2 秒（`JmaClient` で制御）
- リトライ: 最大 3 回 + 指数バックオフ
- 取得単位: 1 リクエスト = 1 ヶ月分
- キャッシュ: `fetch-log` テーブルで取得済み年月を管理し、再取得を防止
