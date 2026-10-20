# backend Lambdaの実行権限

backend実行ロールは配備ロール・通知relayとは別に管理します。

| 対象 | 許可する操作 | 用途 |
| --- | --- | --- |
| stations | GetItem / Scan | 地点・seed version参照 |
| stationsとprec_no-index | Query | 都道府県検索 |
| stations | PutItem / UpdateItem / BatchWriteItem | 起動時seedとmigration |
| daily-temperature | Query / BatchWriteItem | 気温参照・保存 |
| fetch-log | Query / PutItem / GetItem / UpdateItem | 取得履歴と共有lease |
| 自関数log group | CreateLogStream / PutLogEvents | 実行ログ |

handlerはimport時にseed/migrationを行うため、既存データがある場合もstations書込権限を維持します。
BatchWriteItemはbatch DeleteRequestも許可します。DeleteItem除去で全削除を防げるとは扱いません。
自己Invokeや旧scrape-jobsの許可は付けません。旧テーブルのデータは削除しません。
log group作成はTerraformが担当し、movedとcreate_before_destroyで限定policyを先にattachします。
実行ロール自体は維持します。mockテストはtable/index別ARNと操作・ログ配線を確認します。
本番適用は全体planをレビュー・承認し、実policy、新規ログ、通常API、差分なしを確認します。
cache参照だけでmigration・書込成功とせず、未通過の経路を記録します。
AccessDeniedは必要なaction/resourceを特定して通常PRで修正し、データ削除で回避しません。
