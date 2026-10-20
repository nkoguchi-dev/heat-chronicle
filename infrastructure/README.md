# infrastructure

Terraform によるインフラストラクチャの定義です。AWS リソースと GitHub リソースを別ディレクトリで管理しています。

## 構成

```
infrastructure/aws/
├── environments/
│   └── prod/              … 本番環境の Terraform ルート
│       ├── main.tf        … モジュール呼び出し + GitHub Actions OIDC/IAM
│       ├── variables.tf   … 入力変数定義
│       ├── outputs.tf     … 出力値定義
│       ├── provider.tf    … AWS プロバイダ設定
│       ├── backend.tf     … Terraform state 管理（S3）
│       ├── terraform.tfvars.example … 変数のサンプル
│       └── terraform.tfvars.enc    … SOPS + age 暗号化済み変数
└── modules/
    ├── static_site/       … S3 + CloudFront + ACM + Route 53
    └── backend_api/       … ECR + Lambda + API Gateway + DynamoDB

infrastructure/github/
├── main.tf                    … GitHub Actions Secrets / Variables
├── security.tf                … Dependabot alerts / security updates
├── ruleset.tf                 … default branchのPull Request・品質ゲート保護
├── variables.tf               … 入力変数定義
├── outputs.tf                 … 出力値定義
├── provider.tf                … GitHub プロバイダ設定
├── backend.tf                 … Terraform state 管理（S3）
├── terraform.tfvars.example   … 変数のサンプル
└── terraform.tfvars.enc       … SOPS + age 暗号化済み変数

infrastructure/docs/
└── sops-encryption-guide.md   … SOPS + age 暗号化手順書
```

## AWS リソース構成

### フロントエンド (`static_site` モジュール)

- **S3** — 静的ファイルホスティング
- **CloudFront** — CDN 配信 + HTTPS
- **ACM** — SSL/TLS 証明書（us-east-1）
- **Route 53** — カスタムドメイン DNS レコード

### バックエンド (`backend_api` モジュール)

- **ECR** — Docker イメージレジストリ
- **Lambda** — FastAPI アプリケーション（コンテナイメージ）
- **API Gateway (HTTP API)** — REST API エンドポイント + カスタムドメイン
- **DynamoDB** — データキャッシュ（stations / daily-temperature / fetch-log）

### CI/CD

- **IAM OIDC Provider** — GitHub Actions 用の認証
- **IAM Role** — デプロイに必要な最小限の権限（S3, CloudFront, ECR, Lambda）

## GitHub リソース構成

### GitHub Actions (`infrastructure/github/`)

- **Actions Secret** — `AWS_ROLE_ARN`（GitHub Actions OIDC デプロイ用 IAM ロール）
- **Actions Variable** — `AWS_REGION`（デプロイ先 AWS リージョン）
- **Actions Variable** — `CLOUDFRONT_DISTRIBUTION_ID`（CloudFront キャッシュ無効化用）
- **Actions Variable** — `ECR_REPOSITORY_URL`（バックエンド Docker イメージ）
- **Actions Variable** — `LAMBDA_FUNCTION_NAME`（バックエンド Lambda 関数名）
- **Actions Variable** — `VITE_API_URL`（Vite buildに埋め込む公開API origin）
- **Actions Variable** — `S3_BUCKET_NAME`（フロントエンドデプロイ先 S3 バケット）
- **Dependabot alerts** — 脆弱性を含む依存関係の検出
- **Dependabot security updates** — 脆弱な依存関係を更新する Pull Request の自動作成
- **Protect main Ruleset** — mainへのPull Request、non-fast-forward禁止、frontend・backend・Browser Smokeのrequired checks

Dependabot の更新対象と実行スケジュールは `.github/dependabot.yml` で管理しています。

## 使い方

### 前提: SOPS + age のセットアップ

`terraform.tfvars` は SOPS + age で暗号化します。AWS本番の入力は非公開領域で管理し、公開ツリーへ追加しません。GitHub rootの暗号化設定は既存の所有元で管理します。初回セットアップの詳細は [docs/sops-encryption-guide.md](./docs/sops-encryption-guide.md) を参照してください。

```bash
# sops と age のインストール
brew install sops age

# 秘密鍵の配置（既存メンバーから受け取る）
mkdir -p ~/.config/sops/age
vim ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt

# 環境変数の設定（.bashrc / .zshrc に追加）
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
```

### AWS リソース（infrastructure/aws/environments/prod/）

本番入力は所有者の非公開領域で管理します。公開リポジトリへ暗号文を追加しません。
[SOPS入力と保存planの手順](./docs/sops-encryption-guide.md)に従い、最新の所有者入力を
`HEAT_PROD_TFVARS`で指定してください。init時は既存backend bucket/keyを維持し、同じstateを複数rootで管理しません。
本番applyやrelease/prodへの反映は通常PRの統合と分けて承認します。

### GitHub リソース（infrastructure/github/）

```bash
cd infrastructure/github

# AWS 認証情報を設定（S3 バックエンド用）
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
# または AWS CLI プロファイル／IAM ロールで設定済みであれば不要

# GITHUB_TOKEN 環境変数を設定（repo スコープが必要）
export GITHUB_TOKEN="ghp_..."

terraform init

# プロセス置換で復号しながら実行（ディスクに平文が残らない）
terraform plan -var-file=<(sops -d terraform.tfvars.enc)
terraform apply -var-file=<(sops -d terraform.tfvars.enc)
```

`Protect main` Rulesetを変更する場合は、先にworkflowとTerraformコードのPRで4つのcheckが
成功することを確認する。人による確認とmainへのマージ後、最新mainからplanを再実行し、
Ruleset以外の変更やdestroy・replaceがないことを確認してapplyする。apply後はoutputの
`main_ruleset_id`を使い、GitHub APIから実際の設定を再取得する。

```bash
gh api "repos/nkoguchi-dev/heat-chronicle/rulesets/$(terraform output -raw main_ruleset_id)"
```

Rulesetの正本はTerraformとstateであり、通常はGitHubのWeb UIから直接変更しないでください。

### Rulesetのbreak-glass

required checkの改名・削除やworkflowの不具合により、修正PRもmainへマージできなくなった場合に
限り、repository adminが次の手順で一時的に自己ロックを解除します。恒常的なbypass actorは
追加しません。

1. GitHubの`Settings` → `Rules` → `Rulesets` → `Protect main`で、enforcementを`Disabled`へ変更する。
2. 原因と一時無効化をGitHub Issueへ記録し、通常のPull RequestでworkflowまたはRulesetコードを修正する。
3. 修正をmainへ反映した後、最新mainの`infrastructure/github/`からTerraform planを実行する。
4. planが`Protect main`の`active`への復旧だけで、意図しない変更・destroy・replaceを含まないことを確認してapplyする。
5. GitHub APIでRulesetとmainへ適用されるルールを再取得し、復旧結果をIssueへ記録する。

`prevent_destroy`はresource定義が残っている状態での意図しない削除・再作成をplan段階で
停止する。break-glassではRulesetを削除せず、一時的に無効化してTerraformから`active`へ
戻します。

## 注意事項

- `terraform.tfvars`（平文）は `.gitignore` で除外されています。Git には暗号化済みの `terraform.tfvars.enc` のみコミットしてください
- 暗号化・復号の詳細手順は [docs/sops-encryption-guide.md](./docs/sops-encryption-guide.md) を参照してください
- AWS アカウント ID はコード中にハードコードされず、`data.aws_caller_identity` で動的に取得しています
- GitHub Actions のデプロイは OIDC 認証を使用しており、長期的なアクセスキーは不要です
- `infrastructure/github/` の実行には `GITHUB_TOKEN` 環境変数（repo スコープ）が必要です
- GitHub Terraform の変数（`aws_role_arn` 等）は AWS Terraform の output から取得した値です。AWS リソースを再作成した場合は `terraform.tfvars.enc` の値も更新してください

## 公開APIの容量制限

[容量設定と適用確認](./docs/api-capacity.md)に、容量設定の採用値、ローカルmock検証、共有上限と実stateの照合、非本番検証、承認後の本番適用と切り戻しを記載しています。コードのマージと実環境への反映は別に確認します。

## APIの異常検出と通知

API監視のアクセスログ、5種類のAPI/Lambda alarm、Discord通知用LambdaとSSM Standard SecureString、失敗通知の保管、適用・到達確認・対応手順は[APIのログ・異常検出・通知](./docs/api-observability.md)を参照してください。本番反映と通知到達の確認はコードのマージと区別します。

共有費用通知の既存Budgetの所有範囲、費用通知の遅延、通知後の調査・停止判断への導線は[費用通知の対象範囲と対応](./docs/cost-notifications.md)を参照してください。

## AWSの公開境界・実行権限

[公開境界と実行権限の点検](./docs/aws-security-boundary-review.md)に、境界点検で照合した実設定・所有者・未確認範囲と、独立した修正Issueを記録しています。点検の完了と各指摘の修正・本番適用を区別します。

OIDC境界の配備元・許可ref、OIDC subject形式の確認、検証と本番反映手順は[GitHub Actions配備ロールのOIDC境界](./docs/github-oidc-deployment.md)を参照してください。

ECR取得権限のECR policyの所有・既存policyの取り込み・取得権限の縮小と適用確認は[ECRイメージ取得ポリシー](./docs/ecr-image-retrieval.md)を参照してください。

実行権限のテーブル操作と実行IAMの対応、ログ権限移行、適用と確認は[backend Lambdaの実行権限](./docs/lambda-execution-permissions.md)を参照してください。

静的配信のヘッダー方針・互換性確認・適用と切り戻しは[静的配信のセキュリティヘッダー](./docs/static-security-headers.md)を参照してください。

公開APIのCORS契約とGateway/backendの適用・検証は[CORS整合手順](./docs/api-cors.md)を参照してください。
