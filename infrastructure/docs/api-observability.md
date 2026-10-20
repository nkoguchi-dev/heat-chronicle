# APIのログ・異常検出・通知

HTTP APIの専用アクセスログは14日、backend Lambdaログは30日保持します。
アクセスログはrequest ID/time、route template、HTTP/integration/Lambda status、全体/integration時間、response lengthの9項目だけです。
IP・User-Agent・任意path/query/header/body・例外本文を追加しません。request IDをmetric dimensionに使いません。

## 検知と限界

すべて300秒period、GreaterThanOrEqualToThresholdです。

| alarm | 指標 | 閾値・判定 |
| --- | --- | --- |
| API server errors | 5xx Sum | 5件、1 period |
| API latency | Latency Maximum | 25秒、3中2 period |
| Lambda errors | Errors Sum | 1件、1 period |
| Lambda throttles | Throttles Sum | 5件、3中2 period |
| Gateway throttles | ログ429集計 Sum | 10件、3中2 period |

ALARM/OK遷移で通知し、INSUFFICIENT_DATAは通知しません。重複・順序逆転はありえます。
missing dataはnotBreachingのため、無通信停止は検出しません。OKだけで復旧とせず通常APIを確認します。
LambdaのErrorsだけではアプリ503を検出できず、HTTP側と別々に調べます。

## 通知と秘密入力

専用CloudWatch Alarm → SNS → Lambda relay → Discord Incoming Webhookを使用します。
SNSはSourceAccount/SourceArnを限定し、relayもtopic・許可alarmを検証します。
mentionを無効にし、安全なalarm名・状態・時刻・長さを制限したreasonのみを送ります。
Webhookは所有者の非公開SOPS入力からsensitive/ephemeralでSSM Standard SecureStringのvalue_woへ渡します。
URL変更と同時にversionを増やし、通常value・output・環境変数へURLを出しません。
relayは専用parameterだけをWithDecryptionで毎回取得し、SDK例外詳細やURLをログへ出しません。
保存planのapplyにもplan時と同じephemeral入力を渡す必要があります。

SNS呼出失敗とrelay処理失敗を専用暗号化SQSへ14日保管します。
relayは最大2再試行、event age 1時間、Discord timeout 5秒です。
queueのalarmは同じDiscord経路へ通知せず、運用者がqueueとrelayのErrors/Throttles/DeadLetterErrorsを確認します。
Discord自体の障害をDiscordのみで確実に通知できるとは扱いません。自動一括再送はしません。

## 検証と適用

relay unitとTerraform mockは外部接続なしで実行します。
本番は[SOPS入力](./sops-encryption-guide.md)を使った最新全体planを確認し、承認後に適用します。
SSM/stateにURLが通常値として残らないこと、実ログ、alarm、失敗queueを安全な環境で照合します。
通知送信の試験は別途対象・件数・復元を決めて承認し、本人のALARM/OK受信とAPI正常応答を確認します。
機密運用記録や通知先を公開Issueへ貼りません。

障害時は実alarm状態・時刻→HTTP status/所要時間→Lambda指標・ログ→health/通常cache参照の順で確認します。
公開APIの停止・切り戻しは影響と復旧値を示して承認を得ます。通知を消すために上限を緩めません。
