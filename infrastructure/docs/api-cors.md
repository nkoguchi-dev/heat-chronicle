# 公開APIのCORS整合

## 契約と所有

[公開API保護契約](../../docs/API_PROTECTION.md)を正本とし、API Gateway HTTP APIはTerraformのbackend_api module、
アプリ単体はFastAPIのCORSMiddlewareで同じ方針を設定します。CORSは認証ではありません。
frontendのGET実呼び出しと公開OpenAPI/routerを確認してGETのみとし、未使用のpost/put/delete helperを業務契約として扱いません。
APIのroute、fetch-monthの入力・取得制限、CloudFront headerや公開URLは変更しません。

| 項目 | 本番契約 |
|---|---|
| origin | 既存frontendのHTTPS origin 1件 |
| methods | GET（OPTIONSはpreflight処理） |
| request headers | Accept, Accept-Language, Content-Language, Content-Type |
| credentials | false |
| expose headers | Retry-After |
| max_age | 86400（既存Gateway値を維持、アプリも整合） |

[Starlette公式仕様](https://starlette.dev/middleware/#corsmiddleware)のsafelisted headerはアプリで暗黙に許可されるため、Gatewayでも同じ集合を明示します。
frontendはContent-Type: application/jsonを送るためGETでもpreflightが必要です。cross-originのCookie/Authorizationは使用していません。
[HTTP API公式仕様](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html)により、GatewayはOPTIONSを自動処理し、backendから返ったCORS headerを無視します。
backend単体と実Gatewayを別々に確認します。preflightのHTTP statusが同じになることは要求せず、ブラウザが必要なmethod/header/credentialsを許可するかを検証します。

## 検証と配備順

1. ASGI試験で許可GET/preflight、origin null/許可外、POST/PUT/DELETE/HEAD、Authorization/任意header非許可、資格情報なし、Retry-After公開を確認する。実AWS/上流へ接続しない。
2. Terraform fmt/validate/mock planでGateway契約と既存制限を確認。本番読み取りplanがHTTP APIのCORS更新だけで削除/置換なしであることを確認する。
3. backend候補を構築し、既存Container SecurityのTrivy/secret/SBOM gateと隔離handler smokeを実行。source入力と完成digestを記録する。

5. 承認後、候補をECRへpushして同一digestのscan COMPLETE・blockerなしを確認し、同じdigestをLambdaへ反映する。Active/SuccessfulとResolvedImageUriを照合してからGateway planを適用する。
6. 実Gateway設定とCORS応答を照合。許可originのGET・Content-Type preflightが正常、許可外originのACAOがないこと、許可method/headerリストにGET/所定header以外やcredentials trueがなく、Retry-Afterが公開されることを確認する。Gatewayとアプリの拒否statusの同一性を前提にしない。
7. 東京1872年・6都市と通常画面を実ブラウザで確認。AWSログに新しいERROR/AccessDeniedがないこと、適用後plan差分0を確認して証跡を保存する。

本番ではGET /healthとpreflight OPTIONSなど少量の非破壊要求だけを使い、実POST/PUT/DELETE送信や高負荷・強制503・通知試験は行いません。
Retry-Afterの実エラー応答は既存のASGI試験で検証し、本番ではexpose設定と通常応答のheader公開を確認します。
max_age=86400のpreflight cacheが残るため、新しいbrowser contextでも確認します。CORSをAPIの実行禁止や費用対策として扱いません。

## 復旧と現在の状態

不具合時は以前のGateway設定と保持した旧imageを確認し、復旧plan・対象digest・承認を揃えて戻します。旧imageを先に削除せず、CORS更新を戻すためにAPIやデータを削除しません。
