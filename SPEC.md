# heat-chronicle 仕様書

## 概要

日本全国の気象観測地点における過去の日別最高気温データをヒートマップとして可視化するWebアプリケーション。
気象庁が一般公開している「過去の気象データ検索」からデータを取得し、長期的な気温変化の傾向を直感的に把握できるようにする。

## アーキテクチャ

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────┐
│  Frontend   │ ←──→ │    Backend       │ ←──→ │ PostgreSQL   │
│  Next.js    │ API  │  Python FastAPI  │      │  (キャッシュ)  │
└─────────────┘      └───────┬──────────┘      └──────────────┘
                             │ スクレイピング
                             ↓
                     ┌──────────────────┐
                     │  気象庁           │
                     │  過去の気象データ  │
                     └──────────────────┘
```

## 技術スタック

| レイヤー | 技術 | 備考 |
|---------|------|------|
| フロントエンド | Next.js (App Router) | TypeScript, React Server Components |
| バックエンド | Python / FastAPI | 非同期対応 |
| データベース | PostgreSQL 16 | Docker で起動 |
| ORM / DBクライアント | psycopg (Python) | |
| スクレイピング | requests + BeautifulSoup4 | 気象庁HTMLページ解析 |
| ヒートマップ描画 | 未定（候補: D3.js, Plotly.js, Canvas直描画） | フロント側で描画 |

## データソース

### 気象庁 過去の気象データ検索

- ベースURL: `https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php`
- パラメータ:
  - `prec_no`: 都府県・地方番号（2桁）
  - `block_no`: 地点番号（5桁）
  - `year`: 年
  - `month`: 月
  - `day`: （空でよい）
  - `view`: （空でよい）
- 1リクエスト = 1ヶ月分の日別データ（HTMLテーブル）
- アメダス地点の場合は `daily_a1.php` を使用（`daily_s1.php` は気象台・測候所）

### 利用上の注意

- 出典として「気象庁ホームページ」を明記すること
- 過度なアクセスを避けるため、リクエスト間に2秒以上のウェイトを設ける
- 取得したデータはPostgreSQLにキャッシュし、同一データの再取得を防止する

## データベース設計

### stations テーブル（観測地点マスタ）

```sql
CREATE TABLE stations (
    id            SERIAL PRIMARY KEY,
    station_name  VARCHAR(100) NOT NULL,
    prec_no       INTEGER NOT NULL,
    block_no      INTEGER NOT NULL,
    station_type  VARCHAR(1) NOT NULL CHECK (station_type IN ('s', 'a')),
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    UNIQUE (prec_no, block_no)
);
```

| カラム | 型 | 説明 |
|-------|-----|------|
| id | SERIAL | 自動採番 |
| station_name | VARCHAR(100) | 地点名（例: 東京） |
| prec_no | INTEGER | 都府県・地方番号 |
| block_no | INTEGER | 地点番号 |
| station_type | VARCHAR(1) | "s"（気象台）/ "a"（アメダス） |
| latitude | DOUBLE PRECISION | 緯度（任意） |
| longitude | DOUBLE PRECISION | 経度（任意） |

### daily_temperature テーブル（日別気温データ）

```sql
CREATE TABLE daily_temperature (
    id          SERIAL PRIMARY KEY,
    station_id  INTEGER NOT NULL REFERENCES stations(id),
    date        DATE NOT NULL,
    max_temp    REAL,
    min_temp    REAL,
    avg_temp    REAL,
    UNIQUE (station_id, date)
);

CREATE INDEX idx_daily_temp_station_date ON daily_temperature (station_id, date);
```

| カラム | 型 | 説明 |
|-------|-----|------|
| id | SERIAL | 自動採番 |
| station_id | INTEGER | stations.id への外部キー |
| date | DATE | 日付 |
| max_temp | REAL | 日最高気温 (℃) |
| min_temp | REAL | 日最低気温 (℃)（将来の拡張用） |
| avg_temp | REAL | 日平均気温 (℃)（将来の拡張用） |

### fetch_log テーブル（取得履歴）

```sql
CREATE TABLE fetch_log (
    id          SERIAL PRIMARY KEY,
    station_id  INTEGER NOT NULL REFERENCES stations(id),
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (station_id, year, month)
);
```

| カラム | 型 | 説明 |
|-------|-----|------|
| id | SERIAL | 自動採番 |
| station_id | INTEGER | stations.id への外部キー |
| year | INTEGER | 取得済みの年 |
| month | INTEGER | 取得済みの月 |
| fetched_at | TIMESTAMPTZ | 取得日時 |

- このテーブルにレコードがあれば、その年月は再取得しない

## API設計

### GET /api/stations

観測地点一覧を返す。

**レスポンス:**

```json
[
  {
    "id": 1,
    "station_name": "東京",
    "prec_no": 44,
    "block_no": 47662,
    "station_type": "s"
  }
]
```

### GET /api/temperature/{station_id}

指定地点の日別最高気温データを返す。

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| start_year | int | 1975 | 取得開始年 |
| end_year | int | 現在の年 | 取得終了年 |

**レスポンス:**

```json
{
  "station": {
    "id": 1,
    "station_name": "東京"
  },
  "data": [
    { "date": "1975-01-01", "max_temp": 9.8 },
    { "date": "1975-01-02", "max_temp": 8.5 }
  ],
  "metadata": {
    "total_days": 18262,
    "cached_days": 18000,
    "fetching_required": false
  }
}
```

### GET /api/temperature/{station_id}/stream

未キャッシュデータがある場合に、取得進捗をServer-Sent Events (SSE) でストリーミングする。

**イベント:**

```
event: progress
data: {"year": 1975, "month": 3, "total_months": 600, "completed_months": 3}

event: data
data: {"year": 1975, "month": 3, "records": [{"date": "1975-03-01", "max_temp": 12.3}, ...]}

event: complete
data: {"total_records": 18262}

event: error
data: {"message": "気象庁へのアクセスに失敗しました", "year": 1975, "month": 4}
```

## フロントエンド仕様

### 画面構成

```
┌─────────────────────────────────────────────────────┐
│  heat-chronicle                                     │
│  ─────────────────────────────────────────────────  │
│  地点: [東京        ▼]   期間: [1975] 〜 [2025]     │
│                                                     │
│  [データ取得中... 1980年 3月 (60/600)]               │
│  ████████░░░░░░░░░░░░░░░░░ 10%                      │
│                                                     │
│  ヒートマップ:                                       │
│        1月    2月    3月   ...   11月   12月         │
│  1975  ░░░░░  ░░░░░  ▒▒▒▒▒      ░░░░░  ░░░░░      │
│  1976  ░░░░░  ░░░░░  ▒▒▒▒▒      ░░░░░  ░░░░░      │
│  ...                                                │
│  2024  ▒▒▒▒▒  ▒▒▒▒▒  ▓▓▓▓▓      ▒▒▒▒▒  ▒▒▒▒▒      │
│  2025  ▓▓▓▓▓  ▓▓▓▓▓  █████      ▒▒▒▒▒              │
│                                                     │
│  凡例: 0℃ ░░░ 15℃ ▒▒▒ 30℃ ▓▓▓ 40℃ ███            │
│                                                     │
│  出典: 気象庁ホームページ                             │
└─────────────────────────────────────────────────────┘
```

### Next.js ページ構成

| パス | 種別 | 説明 |
|------|------|------|
| `/` | ページ | メインページ（地点選択 + ヒートマップ表示） |

- App Router を使用
- ヒートマップ描画はクライアントコンポーネント（`"use client"`）
- 地点一覧の初期データはサーバーコンポーネントで取得可能

### ヒートマップ仕様

- 横軸: 日（1月1日 〜 12月31日、365/366列）
- 縦軸: 年（デフォルト: 1975 〜 現在年）
- セルの色: 日最高気温を色にマッピング
  - 色スケール: 寒色(青) → 暖色(赤) のグラデーション
  - 範囲: -10℃ 〜 40℃ 程度（地点に応じて動的調整も可）
- マウスホバー: ツールチップで「YYYY年MM月DD日: XX.X℃」を表示
- データ欠損セル: グレーまたは透明で表示

### インタラクション

- 地点選択のプルダウンを変更するとデータ取得・表示が切り替わる
- 初回取得時はSSEで進捗を受信しながら、届いた年のデータからヒートマップに描画する
- 2回目以降の同一地点選択はキャッシュから即座に表示

## 初期収録地点（主要気象台）

初期リリースでは以下の主要気象台を対象とする。

| 地点名 | prec_no | block_no | station_type |
|--------|---------|----------|-------------|
| 札幌 | 14 | 47412 | s |
| 仙台 | 34 | 47590 | s |
| 東京 | 44 | 47662 | s |
| 新潟 | 54 | 47604 | s |
| 名古屋 | 51 | 47636 | s |
| 大阪 | 62 | 47772 | s |
| 広島 | 67 | 47765 | s |
| 高松 | 72 | 47891 | s |
| 福岡 | 82 | 47807 | s |
| 鹿児島 | 88 | 47827 | s |
| 那覇 | 91 | 47936 | s |

※ アメダス地点の追加は将来の拡張とする

## スクレイピング仕様

### 対象ページ

気象台の場合:
```
https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php?prec_no={prec_no}&block_no={block_no}&year={year}&month={month}&day=&view=
```

### HTMLパース

- テーブルは `<table class="data2_s">` で取得
- 行ヘッダ（日付）はtr内の最初のtd
- 日最高気温の列位置は固定（要実データで確認）
- 値が `--` や空白の場合はNULLとして扱う
- 値に `]` や `)` 等の品質フラグ記号が付く場合があるため、数値部分のみ抽出する

### アクセス制御

- リクエスト間隔: 最低2秒
- 1セッションあたりの連続取得上限: 設けない（ウェイトで制御）
- User-Agent: アプリケーション名を含める（例: `heat-chronicle/1.0`）
- エラー時（HTTP 4xx/5xx）: 3回までリトライ、それでも失敗なら該当月をスキップしログに記録

## ディレクトリ構成

```
heat-chronicle/
├── README.md
├── SPEC.md                    # 本ファイル
├── docker-compose.yml         # PostgreSQL + アプリ起動用
├── backend/
│   ├── main.py                # FastAPIアプリケーション
│   ├── database.py            # PostgreSQL接続・テーブル作成
│   ├── models.py              # Pydanticモデル
│   ├── scraper.py             # 気象庁スクレイピング
│   ├── stations.py            # 観測地点マスタデータ
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── next.config.ts
    ├── tsconfig.json
    └── src/
        └── app/
            ├── layout.tsx     # ルートレイアウト
            ├── page.tsx       # メインページ
            └── components/
                ├── StationSelector.tsx
                ├── Heatmap.tsx
                └── ProgressBar.tsx
```

## 環境構築

### PostgreSQL

docker-compose.yml で起動する想定:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: heat_chronicle
      POSTGRES_USER: hc_user
      POSTGRES_PASSWORD: hc_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### バックエンド

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

### 環境変数

| 変数名 | デフォルト | 説明 |
|--------|----------|------|
| DATABASE_URL | postgresql://hc_user:hc_password@localhost:5432/heat_chronicle | PostgreSQL接続文字列 |
| SCRAPE_INTERVAL_SEC | 2 | スクレイピングリクエスト間隔（秒） |
| NEXT_PUBLIC_BACKEND_URL | http://localhost:8000 | フロントエンドからバックエンドへのURL |

## 非機能要件

- 初回データ取得: 1地点あたり最大約20分（50年分、2秒間隔）
- キャッシュ済みデータの応答: 1秒以内
- 同時利用: 単一ユーザー想定（ローカル実行前提）
- ブラウザ対応: Chrome / Firefox / Safari 最新版

## 将来の拡張候補

- アメダス地点への対応拡大
- 日最低気温・日平均気温への切り替え表示
- 年ごとの平均線グラフのオーバーレイ
- 複数地点の比較表示
- データのエクスポート機能（CSV）
- Docker化によるワンコマンド起動（フロント・バックエンド含む）
