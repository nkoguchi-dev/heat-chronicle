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

- **Actions Secret** — `ANTHROPIC_API_KEY`（Claude PR レビュー用）
- **Actions Secret** — `AWS_ROLE_ARN`（GitHub Actions OIDC デプロイ用 IAM ロール）
- **Actions Variable** — `CLAUDE_MAX_TURNS`（Claude の最大ターン数、デフォルト: 20）
- **Actions Variable** — `AWS_REGION`（デプロイ先 AWS リージョン）
- **Actions Variable** — `CLOUDFRONT_DISTRIBUTION_ID`（CloudFront キャッシュ無効化用）
- **Actions Variable** — `ECR_REPOSITORY_URL`（バックエンド Docker イメージ）
- **Actions Variable** — `LAMBDA_FUNCTION_NAME`（バックエンド Lambda 関数名）
- **Actions Variable** — `NEXT_PUBLIC_API_URL`（フロントエンド API エンドポイント）
- **Actions Variable** — `S3_BUCKET_NAME`（フロントエンドデプロイ先 S3 バケット）

## 使い方

### 前提: SOPS + age のセットアップ

`terraform.tfvars` は SOPS + age で暗号化し、`terraform.tfvars.enc` として Git 管理しています。初回セットアップの詳細は [docs/sops-encryption-guide.md](./docs/sops-encryption-guide.md) を参照してください。

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

```bash
cd infrastructure/aws/environments/prod

terraform init

# プロセス置換で復号しながら実行（ディスクに平文が残らない）
terraform plan -var-file=<(sops -d terraform.tfvars.enc)
terraform apply -var-file=<(sops -d terraform.tfvars.enc)
```

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

## 注意事項

- `terraform.tfvars`（平文）は `.gitignore` で除外されています。Git には暗号化済みの `terraform.tfvars.enc` のみコミットしてください
- 暗号化・復号の詳細手順は [docs/sops-encryption-guide.md](./docs/sops-encryption-guide.md) を参照してください
- AWS アカウント ID はコード中にハードコードされず、`data.aws_caller_identity` で動的に取得しています
- GitHub Actions のデプロイは OIDC 認証を使用しており、長期的なアクセスキーは不要です
- `infrastructure/github/` の実行には `GITHUB_TOKEN` 環境変数（repo スコープ）が必要です
- `ANTHROPIC_API_KEY` の値は `terraform.tfvars.enc` に暗号化された状態で含まれています
- GitHub Terraform の変数（`aws_role_arn` 等）は AWS Terraform の output から取得した値です。AWS リソースを再作成した場合は `terraform.tfvars.enc` の値も更新してください
