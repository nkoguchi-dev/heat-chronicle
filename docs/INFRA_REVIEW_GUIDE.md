# インフラ PR レビューガイド

> **前提**: 本ガイドはインフラ固有の観点をまとめたものです。
> 全体共通の観点（コード品質、セキュリティ、環境変数、テスト品質等）は
> [PR レビューガイド（全体共通）](./REVIEW_GUIDE.md) を参照してください。

このドキュメントは、インフラの PR をレビューする際のチェック観点をまとめたものです。
Claude Code によるレビュー自動化、および GitHub Actions の Claude PR Review で使用されます。

対象は `infrastructure/` 配下の Terraform（AWS / GitHub）と、関連する GitHub Actions の
デプロイワークフローです。

---

## 1. 全般・変更管理

- [ ] PR の粒度が適切か（1 つの PR に複数の目的が混在していないか）
- [ ] AWS と GitHub のうち、変更対象となる Terraform ルートすべてで `terraform plan` の結果を確認・共有したか
- [ ] **destroy / replace を含む差分**を入念に確認したか（特に DynamoDB・S3・Terraform state など、失うと復旧が難しいデータやリソースの削除・再作成がないか）
- [ ] `terraform fmt -check -recursive infrastructure` が通るか（整形差分とロジック差分が混在していないか）
- [ ] 対象の Terraform ルートで `terraform validate` が通るか
- [ ] Provider の追加・更新を伴う場合、`.terraform.lock.hcl` の差分が意図通りか

## 2. Terraform 変数と tfvars の同期（最重要）

変数を `variables.tf` に追加・削除・リネームした場合、関連ファイルを必ず同期します。
同期漏れは、本人以外の環境で `terraform plan` が失敗する原因になります。

- [ ] `variables.tf` の変更に合わせて、同じ Terraform ルートの `terraform.tfvars.example`（コミット対象の入力例）を更新したか
- [ ] **default なしの変数を追加した場合**、共有する `terraform.tfvars.enc`（SOPS 暗号化済みの値の源泉）を再暗号化して値を反映したか
  - `terraform.tfvars`（平文）は `.gitignore` 対象で各自のローカル環境にのみ存在するため、ここにだけ値を追加しても他のメンバーには伝わらない
- [ ] 変数をモジュールまで渡す場合、ルートとモジュール双方の `variables.tf`、モジュール呼び出し、参照先を漏れなく更新したか
- [ ] 変数を削除・リネームした場合、`variables.tf` / `.example` / `.enc` / モジュール呼び出しから漏れなく反映され、旧変数名の参照が残っていないか（`git grep <変数名>` で確認）
- [ ] AWS の output を GitHub Actions の Secret / Variable に渡す変更では、以下を一連で更新したか
  - [ ] `infrastructure/aws/environments/prod/outputs.tf`
  - [ ] `infrastructure/github/variables.tf` / `main.tf` / `outputs.tf`
  - [ ] `infrastructure/github/terraform.tfvars.example` / `terraform.tfvars.enc`
  - [ ] 対応する `.github/workflows/deploy-*.yml`

## 3. シークレット・SOPS 暗号化

- [ ] API キー・トークン・認証情報などの機密値が平文でコミットされていないか
- [ ] `terraform.tfvars`（平文）や復号済みファイルが diff に混入していないか
- [ ] 機密を扱う Terraform 変数に `sensitive = true` が指定されているか
- [ ] `terraform.tfvars.enc` の diff が SOPS で暗号化済みであり、平文が漏れていないか
- [ ] 新しい暗号化対象を追加・移動した場合、`.sops.yaml` の `path_regex` と age 公開鍵が正しいか
- [ ] GitHub Actions では、機密値を `github_actions_variable` や `${{ vars.* }}` ではなく Secret として扱っているか
- [ ] Terraform state、`*.tfstate`、`.terraform/` がコミットされていないか（各 `.gitignore` が維持されているか）

## 4. State・リソースのライフサイクル

- [ ] 既存リソースのアドレスが変わるリファクタリングでは、state 移行用の `moved` ブロックを追加したか
- [ ] リソースを `count` / `for_each` 化した場合、既存リソースすべてに対応する `moved` ブロックがあるか
- [ ] リソース名、キー、リージョン、Provider alias の変更で意図しない再作成が発生しないか
- [ ] S3 backend の bucket / key / region の変更が既存 state の参照を失わせないか
- [ ] DynamoDB・S3・ECR などデータを保持するリソースの削除設定（`force_delete` を含む）や保持方針が妥当か
- [ ] CI/CD が更新する属性を Terraform が管理する場合、適切な `lifecycle.ignore_changes` が設定され、実運用と Terraform が競合しないか（例: Lambda の `image_uri`）

## 5. AWS リソース設計

### 共通

- [ ] リソース名が `${system_name}-${environment}-*` の命名規約に沿っているか
- [ ] リソースに共通タグ（`System` / `Environment` / `ManagedBy`）と適切な `Name` タグが付与されているか
- [ ] IAM ポリシーと信頼ポリシーが最小権限になっているか（不要な `Action = "*"` / `Resource = "*"` や広すぎる GitHub OIDC の `sub` 条件がないか）
- [ ] AWS アカウント ID やリソース ARN を不要にハードコードせず、data source・変数・resource 属性から組み立てているか
- [ ] 暗号化、ログ保持、削除保護、バックアップ、監視の要否をリソースの用途に応じて検討したか

### S3・CloudFront・Route 53・ACM

- [ ] S3 の Block Public Access が維持され、CloudFront OAC からのアクセスだけを許可しているか
- [ ] CloudFront の S3 origin に `bucket_regional_domain_name` を使用しているか
- [ ] HTTPS リダイレクトと TLS の最低バージョンが適切か
- [ ] キャッシュ TTL とキャッシュ無効化の運用が、静的アセットと HTML の更新頻度に合っているか
- [ ] 403 / 404 の `custom_error_response` がフロントエンドのルーティング方式と整合しているか
- [ ] CloudFront 用 ACM 証明書に `aws.us_east_1` Provider を使用しているか
- [ ] Route 53 のレコード変更が既存ドメインや証明書検証を壊さないか

### Lambda・API Gateway・DynamoDB・ECR

- [ ] Lambda のメモリ、タイムアウト、環境変数、実行ロールがアプリケーション要件と一致しているか
- [ ] API Gateway の CORS、許可メソッド、カスタムドメイン、Lambda invoke 権限が必要最小限か
- [ ] DynamoDB のパーティションキー・ソートキー・GSI がバックエンドのアクセスパターンと一致しているか
- [ ] DynamoDB の TTL、課金モード、削除・バックアップ方針がデータ特性に合っているか
- [ ] ECR のイメージスキャン、タグ運用、ライフサイクルポリシーがデプロイワークフローと整合しているか

## 6. GitHub リソースとデプロイ連携

- [ ] `infrastructure/github/` で管理する Secret / Variable 名が、ワークフロー内の `${{ secrets.* }}` / `${{ vars.* }}` と一致しているか
- [ ] AWS Terraform の output を変更した場合、GitHub Terraform の入力値と暗号化済み tfvars も更新したか
- [ ] GitHub Actions の OIDC ロールに、変更後のデプロイで必要な権限だけが追加されているか
- [ ] Workflow の `permissions`、トリガー、対象ブランチ、対象パスが意図通りか
- [ ] フロントエンドの S3 同期・CloudFront invalidation、バックエンドの ECR push・Lambda update の各手順に変更が正しく伝播しているか
- [ ] Terraform で管理する GitHub リソースを Web UI や別スクリプトでも変更し、設定ドリフトを生じさせていないか

## 7. 検証

少なくとも変更対象に応じて、以下が通ることを確認します。

```bash
terraform fmt -check -recursive infrastructure

(
  cd infrastructure/aws/environments/prod
  terraform init
  terraform validate
  terraform plan -var-file=<(sops -d terraform.tfvars.enc)
)

(
  cd infrastructure/github
  terraform init
  terraform validate
  terraform plan -var-file=<(sops -d terraform.tfvars.enc)
)
```

- [ ] `terraform plan` が想定した追加・変更・削除だけを含んでいるか
- [ ] インフラ変更の影響を受けるバックエンド / フロントエンドの CI が通るか
- [ ] 本番適用後の確認方法と、失敗時のロールバックまたは復旧手順が明確か

## 8. ドキュメント

- [ ] 変更に応じて `infrastructure/README.md` や `infrastructure/docs/` を更新したか
- [ ] `terraform.tfvars.example` のコメント（用途、形式、値の取得元等）が最新か
- [ ] 新しいリソース、設定項目、初期構築・適用手順、運用上の注意事項をドキュメントに記載したか
- [ ] AWS と GitHub Terraform の依存関係や手動で受け渡す output が変わった場合、その手順を更新したか
