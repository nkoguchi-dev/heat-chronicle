# fetch_stations.py

## 概要

気象庁（JMA）のWebサイトから気温観測地点の一覧をスクレイピングし、CSVファイルに出力するスクリプトです。

## 前提条件

- `backend/` の Poetry 環境がセットアップ済みであること
- 依存パッケージ: `httpx`, `beautifulsoup4`

## 実行方法

```bash
cd backend && poetry run python ../scripts/fetch_stations.py
```

## 出力ファイル

| ファイル | 内容 |
|---------|------|
| `backend/data/stations_YYYYMMDD.csv` | 地点一覧（列: `prec_no,station_name,block_no,station_type`） |
| `backend/data/prefectures_YYYYMMDD.txt` | 都道府県マッピング（`prefectures.py` 更新用の Python dict リテラル） |

## 処理内容

1. JMA のトップページ（`prefecture00.php`）から都道府県一覧を取得
2. 各都道府県ページの `<area>` タグに含まれる `viewPoint(...)` をパース
3. `f_temp >= 1`（気温観測あり）の地点のみ抽出
4. `prec_no` → `station_name` の順でソートしてCSVに出力

## レート制限

JMA サーバーへの負荷軽減のため、リクエスト間隔を **2秒** 空けています。全都道府県の処理に **約2分** かかります。

## 注意事項

- JMA サイトの HTML 構造（`viewPoint()` の引数レイアウトなど）が変更された場合、パース処理の修正が必要です。
- `block_no` の重複は自動的に除外されます（都道府県ページ内で同一地点が複数回出現する場合があるため）。
