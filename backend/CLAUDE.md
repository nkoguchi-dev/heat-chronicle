# Backend CLAUDE.md

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
| Application | `application/` | ビジネスロジック（スクレイピング、キャッシュ判定） |
| Domain | `domain/` | Pydantic レスポンススキーマ |
| Infrastructure | `infrastructure/` | DynamoDB アクセス、気象庁スクレイパー |

### レイヤー間の制約

- **Presentation → Application**: ルーターはサービス層のみを呼び出す
- **Presentation → Infrastructure**: 直接呼び出し禁止（必ず Application 層を経由する）
- **Application → Infrastructure**: リポジトリ・スクレイパーを利用可能
- **Domain**: 他レイヤーに依存しない（純粋なスキーマ定義）
- **Infrastructure → Application/Presentation**: 逆方向の依存禁止

## 主要パターン

- **リポジトリパターン**: `StationRepository` と `TemperatureRepository` が全 DB クエリをカプセル化
- **依存性注入**: FastAPI の `Depends` を使用（`StationRepoDep`, `TempRepoDep`）
- **レート制限スクレイピング**: `JmaClient` がリクエスト間隔 2 秒以上を強制、3 回リトライ + 指数バックオフ

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
