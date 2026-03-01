# Claude PR レビュー用 Anthropic API キー
resource "github_actions_secret" "anthropic_api_key" {
  repository      = var.github_repository
  secret_name     = "ANTHROPIC_API_KEY"
  plaintext_value = var.anthropic_api_key
}

# Claude の最大ターン数
resource "github_actions_variable" "claude_max_turns" {
  repository    = var.github_repository
  variable_name = "CLAUDE_MAX_TURNS"
  value         = tostring(var.claude_max_turns)
}

# --- AWS デプロイ関連 ---

resource "github_actions_secret" "aws_role_arn" {
  repository      = var.github_repository
  secret_name     = "AWS_ROLE_ARN"
  plaintext_value = var.aws_role_arn
}

resource "github_actions_variable" "aws_region" {
  repository    = var.github_repository
  variable_name = "AWS_REGION"
  value         = var.aws_region
}

resource "github_actions_variable" "cloudfront_distribution_id" {
  repository    = var.github_repository
  variable_name = "CLOUDFRONT_DISTRIBUTION_ID"
  value         = var.cloudfront_distribution_id
}

resource "github_actions_variable" "ecr_repository_url" {
  repository    = var.github_repository
  variable_name = "ECR_REPOSITORY_URL"
  value         = var.ecr_repository_url
}

resource "github_actions_variable" "lambda_function_name" {
  repository    = var.github_repository
  variable_name = "LAMBDA_FUNCTION_NAME"
  value         = var.lambda_function_name
}

resource "github_actions_variable" "next_public_api_url" {
  repository    = var.github_repository
  variable_name = "NEXT_PUBLIC_API_URL"
  value         = var.next_public_api_url
}

resource "github_actions_variable" "s3_bucket_name" {
  repository    = var.github_repository
  variable_name = "S3_BUCKET_NAME"
  value         = var.s3_bucket_name
}
