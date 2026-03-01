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
│       └── terraform.tfvars.example … 変数のサンプル
└── modules/
    ├── static_site/       … S3 + CloudFront + ACM + Route 53
    └── backend_api/       … ECR + Lambda + API Gateway + DynamoDB

infrastructure/github/
├── main.tf                    … GitHub Actions Secrets / Variables
├── variables.tf               … 入力変数定義
├── outputs.tf                 … 出力値定義
├── provider.tf                … GitHub プロバイダ設定
├── backend.tf                 … Terraform state 管理（S3）
└── terraform.tfvars.example   … 変数のサンプル
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
- **Actions Variable** — `CLAUDE_MAX_TURNS`（Claude の最大ターン数、デフォルト: 20）

## 使い方

### AWS リソース（infrastructure/aws/environments/prod/）

```bash
cd infrastructure/aws/environments/prod

# terraform.tfvars を作成（サンプルからコピー）
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集してドメイン名などを設定

# 初期化
terraform init

# プラン確認
terraform plan

# 適用
terraform apply
```

### GitHub リソース（infrastructure/github/）

```bash
cd infrastructure/github

# terraform.tfvars を作成（サンプルからコピー）
cp terraform.tfvars.example terraform.tfvars
# ANTHROPIC_API_KEY の実際の値を記入

# GITHUB_TOKEN 環境変数を設定（repo スコープが必要）
export GITHUB_TOKEN="ghp_..."

terraform init
terraform plan
terraform apply
```

## 注意事項

- `terraform.tfvars` は `.gitignore` で除外されています（機密情報を含む可能性があるため）
- AWS アカウント ID はコード中にハードコードされず、`data.aws_caller_identity` で動的に取得しています
- GitHub Actions のデプロイは OIDC 認証を使用しており、長期的なアクセスキーは不要です
- `infrastructure/github/` の実行には `GITHUB_TOKEN` 環境変数（repo スコープ）が必要です
- `ANTHROPIC_API_KEY` の値は `terraform.tfvars` に記載するため、環境変数としての設定は不要です
