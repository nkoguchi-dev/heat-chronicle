# database

ローカル開発用の DynamoDB Local データディレクトリです。

## 概要

`docker compose up dynamodb-local` で起動する DynamoDB Local が、このディレクトリにデータファイルを永続化します。`compose.yaml` でボリュームマウントされており、コンテナを再起動してもデータが保持されます。

## DynamoDB テーブル構成

バックエンド起動時に自動作成される 3 テーブル:

| テーブル名 | 用途 | パーティションキー | GSI |
|-----------|------|-------------------|-----|
| `stations` | 気象観測地点マスタ | `id` (N) | `prec_no-index` (prec_no → id) |
| `daily-temperature` | 日別気温レコード | `station_id#date` (S) | — |
| `fetch-log` | スクレイピング取得履歴 | `station_id#year_month` (S) | — |

## ファイル

```
database/
└── data/
    └── shared-local-instance.db   … DynamoDB Local の SQLite データファイル
```

`data/` ディレクトリは `.gitignore` で除外されており、Git には含まれません。

## 注意事項

- このディレクトリの内容はローカル開発専用です
- 本番環境では AWS の DynamoDB サービスを直接使用します
- データファイルを削除すると、ローカルのキャッシュデータがすべて失われます
