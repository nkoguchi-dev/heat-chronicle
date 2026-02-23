# heat-chronicle

日本全国の気象観測地点における **日別最高気温** をヒートマップとして可視化する Web アプリケーションです。
気象庁が公開している「過去の気象データ検索」からデータを取得し、長期的な気温変化の傾向を直感的に把握できます。

**サイト URL:** https://heat-chronicle.koppepan.org

## 主要都市のヒートマップ

| 地点 | リンク |
|------|--------|
| 札幌 | [heat-chronicle.koppepan.org/?pref=14&station=1](https://heat-chronicle.koppepan.org/?pref=14&station=1) |
| 仙台 | [heat-chronicle.koppepan.org/?pref=34&station=2](https://heat-chronicle.koppepan.org/?pref=34&station=2) |
| 東京 | [heat-chronicle.koppepan.org/?pref=44&station=4](https://heat-chronicle.koppepan.org/?pref=44&station=4) |
| 名古屋 | [heat-chronicle.koppepan.org/?pref=51&station=6](https://heat-chronicle.koppepan.org/?pref=51&station=6) |
| 大阪 | [heat-chronicle.koppepan.org/?pref=62&station=7](https://heat-chronicle.koppepan.org/?pref=62&station=7) |
| 広島 | [heat-chronicle.koppepan.org/?pref=67&station=8](https://heat-chronicle.koppepan.org/?pref=67&station=8) |
| 福岡 | [heat-chronicle.koppepan.org/?pref=82&station=10](https://heat-chronicle.koppepan.org/?pref=82&station=10) |
| 那覇 | [heat-chronicle.koppepan.org/?pref=91&station=12](https://heat-chronicle.koppepan.org/?pref=91&station=12) |

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| フロントエンド | Next.js 16 / React 19 / TypeScript / Tailwind CSS v4 |
| バックエンド | Python 3.12 / FastAPI / BeautifulSoup4 |
| データベース | Amazon DynamoDB（ローカル開発は DynamoDB Local） |
| インフラ | AWS Lambda + API Gateway / S3 + CloudFront / Terraform |
| CI/CD | GitHub Actions（OIDC 認証） |

## アーキテクチャ

```
┌─────────────────┐     ┌────────────────────┐     ┌───────────┐
│  Frontend       │────→│  Backend (Lambda)  │────→│ DynamoDB  │
│  S3+CloudFront  │ API │  FastAPI + Mangum  │     │ (キャッシュ) │
└─────────────────┘     └────────┬───────────┘     └───────────┘
                                 │ スクレイピング
                                 ↓
                        ┌────────────────────┐
                        │  気象庁             │
                        │  過去の気象データ    │
                        └────────────────────┘
```

フロントエンドは静的エクスポートされた Next.js アプリを S3 + CloudFront で配信し、バックエンドは Lambda（コンテナイメージ）上で FastAPI を実行しています。気象庁から取得したデータは DynamoDB にキャッシュされ、同一データの再取得を防止します。

## ディレクトリ構成

```
heat-chronicle/
├── backend/           … Python/FastAPI バックエンド
├── frontend/          … Next.js フロントエンド
├── database/          … DynamoDB Local のデータファイル
├── infrastructure/    … Terraform による AWS インフラ定義
├── scripts/           … データ取得・デプロイ用ユーティリティスクリプト
├── .github/workflows/ … GitHub Actions CI/CD
├── compose.yaml       … Docker Compose（ローカル開発用）
└── SPEC.md            … 詳細仕様書
```

各ディレクトリの詳細は、それぞれの `README.md` を参照してください。

## ローカル開発

### 前提条件

- Docker / Docker Compose
- Python 3.12+ / Poetry
- Node.js 22+ / npm

### クイックスタート（Docker Compose）

```bash
docker compose up
```

DynamoDB Local（ポート 8001）、バックエンド（ポート 8000）、フロントエンド（ポート 3000）がすべて起動します。

### 個別起動

```bash
# DynamoDB Local のみ起動
docker compose up dynamodb-local

# バックエンド
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000

# フロントエンド
cd frontend
npm install
npm run dev
```

### 環境変数

各サービスの `.env.local` で設定します（`.gitignore` で除外済み）。

**backend/.env.local:**

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `DYNAMODB_ENDPOINT_URL` | *(なし)* | DynamoDB Local の URL（ローカル開発時: `http://localhost:8001`） |
| `DYNAMODB_REGION` | `ap-northeast-1` | AWS リージョン |
| `DYNAMODB_TABLE_PREFIX` | *(なし)* | テーブル名のプレフィックス |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | CORS 許可オリジン |

**frontend/.env.local:**

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `NEXT_PUBLIC_API_URL` | *(なし)* | バックエンド API の URL（ローカル開発時: `http://localhost:8000`） |

## 初期データの作成

観測地点のマスタデータは `backend/data/stations.json` に格納されています。このファイルは以下のスクリプトで生成・更新できます。すべて `backend/` ディレクトリの Poetry 環境を使って実行します。

### 1. 観測地点一覧の取得

気象庁のWebサイトから気温観測を行っている全地点をスクレイピングし、CSV を出力します。

```bash
cd backend && poetry run python ../scripts/fetch_stations.py
```

出力: `backend/data/stations_YYYYMMDD.csv`, `backend/data/prefectures_YYYYMMDD.txt`

処理には約 2 分かかります（リクエスト間隔 2 秒 × 全都道府県）。

### 2. 各地点の最古データ年の取得

`stations.json` の各地点について、気象庁で閲覧可能な最も古い年を取得し `earliest_year` フィールドを追加します。

```bash
cd backend && poetry run python ../scripts/fetch_earliest_years.py
```

出力: `backend/data/stations.json`（上書き更新）, `backend/data/earliest_years_YYYYMMDD.csv`

全地点を巡回するため、地点数に応じて相応の時間がかかります（979 地点 × 2 秒 ≈ 約 33 分）。

### 3. マイグレーションファイルの生成（旧 PostgreSQL 環境用）

地点 CSV から Alembic マイグレーションファイルを生成するスクリプトです。現在の DynamoDB 環境では直接使用しませんが、参考として残しています。

```bash
# 全件 INSERT
cd backend && poetry run python ../scripts/generate_migration.py data/stations_YYYYMMDD.csv

# 差分更新（新旧 CSV の比較）
cd backend && poetry run python ../scripts/generate_migration.py data/stations_old.csv data/stations_new.csv
```

### 初期データの自動投入

バックエンドの起動時に `backend/data/stations.json` から DynamoDB の `stations` テーブルへ自動的にシードデータが投入されます（マイグレーション管理付き）。手動でのデータ投入は不要です。

## デプロイ

`release/prod` ブランチへの push で GitHub Actions が自動デプロイを実行します。

- **フロントエンド:** `npm run build` → S3 へアップロード → CloudFront キャッシュ無効化
- **バックエンド:** Docker イメージビルド → ECR へプッシュ → Lambda 関数コード更新

詳細は `.github/workflows/` 配下のワークフロー定義を参照してください。

## データ出典

このアプリケーションで使用している気象データは、[気象庁ホームページ](https://www.jma.go.jp/)「過去の気象データ検索」から取得しています。

## ライセンス

このプロジェクトは個人プロジェクトです。
