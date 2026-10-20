# 容量制御用一時環境

API GatewayとLambdaの制限を実AWSで切り分ける固定応答fixture。
**実アプリ、DynamoDB、気象庁、共有lease、UIを動かさない。**
実アプリの2閲覧者・キャッシュ維持・25秒取得予算の確認は、別の検証として残る。
本番のTerraform state、既存Lambda、DNS、ECR、OIDCを参照・更新しない。ローカルstateを使う。

## 作成前に確認する範囲

- 専用の新規リソース10個：HTTP API、integration、route 2個、stage、Lambda、invoke permission、IAM role、log書き込みpolicy、保持1日のlog group。
- IAMはLambdaのassumeと専用log groupへの書き込みのみ。データアクセス・外部呼び出し・自己Invoke権限なし。
- stage 5/10、月別route 1/2、予約同時実行5。Lambdaは128MiB・timeout 10秒、固定遅延は6秒。
- APIは匿名公開。予測困難なAPI IDやCORSはアクセス制御ではない。未要求の外部アクセスによる費用は上限保証できない。
- 従量課金のLambda・HTTP API・CloudWatch Logsを使う。検証ツールはHTTP最大29回＋同期Invoke最大8回、SDK再試行なし。Lambdaの自動非同期再試行も使わない。
- 自己生成した37回が全て10秒動いた場合、計算量の上限は46.25 GB秒。この値は請求額や外部アクセスの上限ではない。料金・共有枠は実施前に確認する。
- 作成から削除まで最大1時間の一時利用を提案する。自動削除機構はなく、実施者が終了直後にdestroyし、失敗時も削除完了を確認する。
- 作成・検証・この専用資源の削除を一組として承認を得る。本番apply・本番負荷試験は含めない。

## AWSを変更しない検証

```sh
python3 infrastructure/aws/environments/capacity-test/package.py
python3 -m unittest discover -s infrastructure/aws/environments/capacity-test -p 'test_*.py'
terraform -chdir=infrastructure/aws/environments/capacity-test init -backend=false -lockfile=readonly
terraform -chdir=infrastructure/aws/environments/capacity-test validate
terraform -chdir=infrastructure/aws/environments/capacity-test test
```

AWS providerはfixture専用lockの6.67.0。prodのlockとは独立して検証する。fixture.zipは決定的に生成し、Gitへ保存しない。
mockは実APIの429・Lambda拒否・回復を確認しない。CIはここまで実行し、applyやprobeは実行しない。

## 承認後に実施する操作

対象profile・アカウント・リージョン、未予約枠に5を追加しても100以上残ること、他サービスへの影響を再確認する。
HEAT_FIXTURE_DIRへ所有者専用ディレクトリを設定する。以下はリポジトリルートから実行する。planとstateを別ディレクトリやprodへ持ち替えない。

```sh
# AWS_PROFILEへ承認された隔離環境のprofileを設定する。
python3 infrastructure/aws/environments/capacity-test/package.py
terraform -chdir=infrastructure/aws/environments/capacity-test plan -var=test_id=review-example -out=${HEAT_FIXTURE_DIR:?}/fixture.tfplan
# 保存planの10件を再レビューし、承認対象と一致することを確認
terraform -chdir=infrastructure/aws/environments/capacity-test apply ${HEAT_FIXTURE_DIR:?}/fixture.tfplan
terraform -chdir=infrastructure/aws/environments/capacity-test output -json > ${HEAT_FIXTURE_DIR:?}/test-output.json
python3 infrastructure/aws/environments/capacity-test/probe.py \
  ${HEAT_FIXTURE_DIR:?}/test-output.json \
  --confirm-function heat-capacity-review-example \
  --result ${HEAT_FIXTURE_DIR:?}/results.json
```

probeは専用名・環境タグ・API IDとendpoint・予約枠をAWSで照合する。HTTP redirectは追わない。
2利用者×3回、固定503のRetry-After/CORS、12件の月別burst、8件の遅延HTTP、8件の直接Invoke、停止後の回復を順に確認する。
best effortのため拒否件数は固定しない。429やLambda拒否を観測できない場合も成功にせず、結果を確認して実施条件を見直す。自動で回数を増やさない。
通信例外でも取得済みのphase結果を保存する。HTTPクライアントの15秒timeoutは30秒以内成功の証明ではなく失敗として扱う。

**probe失敗時も削除を省略しない。** ローカルstateを失う前に、専用10件だけを対象とするdestroy planを確認する。

```sh
terraform -chdir=infrastructure/aws/environments/capacity-test plan -destroy -var=test_id=review-example -out=${HEAT_FIXTURE_DIR:?}/destroy.tfplan
terraform -chdir=infrastructure/aws/environments/capacity-test apply ${HEAT_FIXTURE_DIR:?}/destroy.tfplan
terraform -chdir=infrastructure/aws/environments/capacity-test state list
```

最後のstate listが空であることと、AWSでAPI・関数・IAM role・log groupが残っていないことを確認する。
state・zip・planはコミットしない。結果は非公開PRに要約し、実施日時・対象commit・失敗と限界を残す。

[容量設定と適用確認](../../../docs/api-capacity.md)へ戻る。
