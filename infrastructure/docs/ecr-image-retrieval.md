# ECRイメージ取得ポリシー

ECRとrepository policyは、このリポジトリのAWS prod rootで一元管理します。
`imports.tf`は既存policyをrepository名で宣言的に取り込みます。管理済みstateでは再importしません。
別rootで同じ資源を管理せず、作業場所の移動でbackend bucket/keyを変更しません。

- principalは`lambda.amazonaws.com`。
- actionは`ecr:BatchGetImage` / `ecr:GetDownloadUrlForLayer`。
- `ArnEquals`の`aws:SourceArn`は対象backend関数のみ。

policy管理者とimageを取得するLambdaサービスの権限を分離します。
[AWSのコンテナ権限](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)を参照してください。
mockテストは生成policyとrepositoryへの配線を確認し、実IAM評価やpull成功は保証しません。
本番変更は通常の全体planのimport・変更・削除・置換をレビューして承認後に適用します。
実policy、state address、plan差分なし、Lambda状態と通常APIを確認します。
cache応答だけで新規pull成功とせず、承認済み配備で新digestのActive/Successfulを確認します。
使用中・切り戻し先のimageやpolicyを削除する試験は行いません。
