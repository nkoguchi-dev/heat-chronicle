# generate_migration.py

## 概要

地点一覧の CSV ファイルから Alembic マイグレーションファイルを自動生成するスクリプトです。地点データを Python リテラルとしてマイグレーションファイル内にハードコードします。

## 前提条件

- `backend/` ディレクトリから実行すること（`alembic/versions/` の存在が必須）

## 実行方法

### 全件 INSERT（初期シード）

```bash
cd backend && poetry run python ../scripts/generate_migration.py data/stations_YYYYMMDD.csv
```

### 差分更新（地点の追加・削除）

```bash
cd backend && poetry run python ../scripts/generate_migration.py data/stations_old.csv data/stations_new.csv
```

## 出力ファイル

`backend/alembic/versions/v{NNN}_{description}.py`

バージョン番号（`NNN`）は `alembic/versions/` 内の既存ファイルから自動採番されます。

## モードの説明

### CSV 1つ（全件 INSERT）

CSV の全行を `INSERT INTO heat.stations ... ON CONFLICT DO NOTHING` として出力します。既存データとの重複は無視されます。

### CSV 2つ（差分更新）

`(prec_no, block_no)` をキーとして新旧 CSV の差分を計算し、INSERT / DELETE を生成します。

- 新 CSV にのみ存在する地点 → INSERT
- 旧 CSV にのみ存在する地点 → DELETE

差分がない場合は `No changes detected between CSVs.` と出力して終了します（ファイルは生成されません）。

## downgrade の挙動

`heat.daily_temperature` にデータが紐づいている地点は FK 制約保護のため削除しません（`id NOT IN (SELECT DISTINCT station_id FROM heat.daily_temperature)` で除外）。

## 典型的な運用フロー

```bash
# 1. 最新の地点一覧を取得
cd backend && poetry run python ../scripts/fetch_stations.py

# 2. 既存 CSV と差分を確認
diff data/stations_old.csv data/stations_YYYYMMDD.csv

# 3. 差分マイグレーションを生成
poetry run python ../scripts/generate_migration.py data/stations_old.csv data/stations_YYYYMMDD.csv

# 4. マイグレーション適用
poetry run alembic upgrade head
```
