# 公開APIの容量設定と適用確認

#199 / 親 #195。採用値と利用者向け契約は[API保護契約](../../docs/API_PROTECTION.md)を正本とする。
本書はTerraformの検証・段階適用・切り戻しの手順。コードの追加だけで実環境へ適用済みとは扱わない。

## 設定と影響

prodルートの`api_capacity`からbackend_apiモジュールへ値を渡す。初期値はstage rate 5 / burst 10、
月別取得route rate 1 / burst 2、Lambda reserved concurrency 5。
月別routeは`GET /api/temperature/{station_id}/fetch-month`を明示し、既存のLambda integrationへ転送する。
他の経路は既存の`$default`へ転送する。HTTP API CORSで`Retry-After`を公開する。

rateは正数、burstとconcurrencyは正整数、月別routeのrate・burstはstage既定値以下を入力契約とする。
0による停止は通常の容量設定と混ぜず、#206の停止手順で扱う。データテーブル、Lambda image、IAM、DNSの変更は追加しない。
`api_capacity`のdefaultがあるため、既存の暗号化tfvarsへの追記は不要。個別環境で変更する場合は入力例と同じobjectを指定する。

stageの既定値はrouteごとの既定設定であり、API全体をまとめた5rpsの厳密な上限を作るものではない。
明示routeの設定が優先され、アカウント・リージョンの上限も別途適用される。
API Gatewayのrate/burstはbest effortであり、Lambda同時実行の上限も厳密な費用上限を保証しない。

Lambdaのreserved concurrencyはHTTP経路・直接Invoke・内部呼び出しで共有する。
2026-10-19のmain `2b3db59`ではbackend/appとscriptsにLambda Invoke呼び出しは見つからないが、
Terraformには自己InvokeのIAM権限が残る。実際の呼び出し元・イベント設定はAWSで別途確認し、未確認を不存在と扱わない。
IAM整理は#204の範囲とする。API Gatewayを通らないInvokeにHTTP側のrate制限は効かない。

## AWSを変更しないローカル検証

Terraform 1.16.3で確認する。providerは既存lockfileに固定したAWS 6.67.0を使い、更新しない。
テストはmock providerをplan中から使用し、実AWSへの接続・リソース作成をしない。

```sh
terraform fmt -check -recursive infrastructure
terraform -chdir=infrastructure/aws/environments/prod init -backend=false -lockfile=readonly -input=false
terraform -chdir=infrastructure/aws/environments/prod validate
terraform -chdir=infrastructure/aws/environments/prod test
```

正例は既定経路と月別経路の配線、容量値、Retry-After公開を確認する。
負例はconcurrency 0、stageより大きい月別rate、小数のburstを拒否する。
mock planは実AWSの受理、既存stateとの差分、アカウント余力、実際の429や回復を確認しない。

## 実設定と共有上限の確認（適用前）

AWS SSOを認証し、所有するアカウントとリージョンが対象環境であることをローカルで照合する。
アカウント識別子、ARN、通知先、state、未加工のplanを公開IssueやPRへ貼らない。

1. Lambdaのget-account-settingsで総上限と未予約枠、get-function-concurrencyで対象関数の現在の予約値を取得する。
   新しい予約値を入れた後も、他の予約を除いた未予約枠100以上を維持できることと、他サービスの通常需要を確認する。
2. HTTP APIのget-apis / get-routes / get-stagesで実route、DefaultRouteSettings、RouteSettings、CORSを照合する。
   API Gatewayのアカウント上限とリージョン共有の利用状況を確認する。
3. Lambdaのイベントソース・呼び出し元・非同期Invokeの有無を確認する。直接Invokeも同じ5枠を使う。
4. 現在値と確認日、他サービスへの影響判断を記録する。確認できない場合は適用へ進まない。

## 実stateに対するplan

AWS用の対象profileを設定し、prodルートから実行する。planは機密を含みうるためGit管理外のローカルに保管する。

```sh
cd infrastructure/aws/environments/prod
terraform init -lockfile=readonly
terraform validate
terraform plan -var-file=<(sops -d terraform.tfvars.enc) -out=/private/tmp/heat-capacity.tfplan
```

想定する差分は月別routeの追加と、stageの設定・Lambda同時実行・API CORSの更新。
削除・再作成が0件で、IAM、DynamoDB、DNS、image、他サービスを変更しないことを確認する。
既存ドリフトが混ざる場合は理由を調査し、`-target`で隠して適用しない。
stateに無かった既存リソースがある場合も、新規作成と決めつけず所有を確認する。

## 非本番での検証

本リポジトリには現時点で専用の非本番Terraformルートはない。
既存の検証環境を利用できるか、または固定上流・専用資源による一時環境の構築範囲と費用を合意してから配備する。
prodを検証先に読み替えない。mock providerの成功を、この段の完了に代用しない。

- 固定の上流応答と専用データを使い、2利用者が各1本ずつ月別取得し、応答後2秒以上待つ操作を確認する。
  キャッシュ参照、月別取得の成功または競合503、Retry-Afterに従う手動再試行とデータ維持を確認する。
- 許可した検証環境だけで、短い制御された集中要求によりGatewayの429を観測する。
  具体的な要求数・実行時間は事前に決め、best effortのため閾値ぴったりの拒否件数を前提にしない。
- 固定応答の遅延を使ってLambdaの同時実行枠を検証し、上限超過時のInvoke拒否とGatewayから見える応答を分けて記録する。
- 要求を止めて待ち、通常の参照と月別取得が回復すること、CORS経由でRetry-Afterを読めることを確認する。
- HTTP全体の応答時間も測定する。#198の25秒予算に同期DB処理等は別途加算されるため、Gatewayの待ち時間内に収まるか確認する。
  収まらない場合は本番適用前に契約を見直す。

## 本番への段階適用と切り戻し

人のPRレビュー・マージ、最新mainの再plan、上記の非本番検証の後に、具体的なplanを示して本番適用の承認を得る。
#198のアプリケーション版が本番に反映され、制限時の停止・待機・手動再試行が利用できることも先に確認する。
承認された最新の保存planをapplyし、route・stage・CORS・Lambdaの実値を再取得する。
通常の本番スモークはAGENTS.mdの手順を用い、本番負荷試験は行わない。

失敗時は、事前に記録した値へTerraformコードを戻して別のplanを作り、人の確認後に適用する。
今回追加した明示routeとRouteSettings、CORS expose_headers、reserved concurrencyを一組で扱う。
予約の解除には既存設定に応じて`reserved_concurrent_executions = -1`を使う別変更が必要であり、通常入力の0に置き換えない。
未予約への復帰は共有枠へ負荷を戻すため、他サービスへの影響も再確認する。state編集や手動のAPI更新を通常の切り戻し手段にしない。

## 実施状況（2026-10-19）

コードとmock planテスト4件を追加し、fmt・validate・4件すべての成功をローカルで確認済み。
PRとmainで同じオフライン検証を実行するCIも追加し、追加CIを含む5チェックの成功を確認した。
AWS providerのバージョン6.67.0は維持し、Linux検証用の公式署名済みハッシュをlockfileへ追加した。

SSO再認証後、実AWSの読み取りとS3 backend初期化、暗号化tfvarsを用いた実state planに成功した。
アカウント識別子・ARN・state・生のplanは公開文書へ保存しない。

| 対象 | 読み取り結果 | この変更での計画 |
| --- | --- | --- |
| Lambda共有枠 | リージョン上限1,000、未予約1,000、対象予約なし | 対象へ5枠を予約し、未予約995を残す |
| 同リージョンのLambda | 一覧で1関数。過去14日のaccount concurrency最大12、得られた時間別データ53点 | 5枠による既存利用への影響は未検証 |
| HTTP API | `$default` routeのみ、stageのrate/burstとroute設定なし | 月別route追加、stage 5/10、月別1/2 |
| API Gateway共有上限 | rate 10,000 / burst 5,000 | アカウント上限は変更しない |
| HTTP API CORS | expose headerなし | Retry-Afterを公開 |
| API integration | AWS_PROXY、payload 2.0、待ち時間30,000ms | integrationの変更なし |
| Lambda呼び出し設定 | event source mappings 0、event invoke configs 0、resource policyはAPI Gatewayのservice principalのみ | 呼び出し許可は変更しない |

CloudWatchのデータは欠測を含む観測値であり、最大12が通常利用か異常アクセスかは未判別。
他のLambda関数が同リージョンにないことは確認したが、5枠への制限が既存利用へ影響しないとは判断しない。
event sourceやresource policyだけではIAM権限による直接Invokeの有無を証明できず、呼び出し元の完全な追跡は未実施。

実state planは以下の4リソースだけを変更する。**追加1・更新3・削除0・再作成0**で、
IAM、データテーブル、DNS、image変更は含まない。

- `module.backend_api.aws_apigatewayv2_route.fetch_month`: 追加、既存integrationへ転送
- `module.backend_api.aws_apigatewayv2_stage.default`: defaultと月別routeの容量設定を更新
- `module.backend_api.aws_apigatewayv2_api.backend`: CORS expose_headersを更新
- `module.backend_api.aws_lambda_function.backend`: reserved_concurrent_executionsを5へ更新

refreshで検出したLambdaのimage_uri・code_sha256・last_modified差分は、既存のActions配備と整合する。
image_uriは既存ignore_changesにより、このplanでは変更しない。
実稼働Lambdaのresolved digestはECRの`5e32a6bc69e7723cd67d15a293a2b0304c5a34d0`タグと一致し、Active / Successfulを確認した。
release/prodも同commitで、#198を含むmain `2b3db59`は本番未反映。

非本番での2利用者・上限超過・回復と30秒以内の応答、本番へのアプリ先行反映、
容量設定の承認・適用・適用後確認は未実施。これらが残るためDraft PRと#199のopenを維持する。
本番へのapply・負荷試験は行っていない。

## 一次資料

- [HTTP APIのthrottling](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-throttling.html)
- [Lambda reserved concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
- [AWS provider 6.67.0のstage設定](https://github.com/hashicorp/terraform-provider-aws/blob/v6.67.0/website/docs/r/apigatewayv2_stage.html.markdown)
- [Terraformのmock provider](https://developer.hashicorp.com/terraform/language/tests/mocking)
