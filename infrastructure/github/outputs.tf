output "anthropic_api_key_created_at" {
  description = "ANTHROPIC_API_KEY secret creation timestamp"
  value       = github_actions_secret.anthropic_api_key.created_at
}

output "claude_max_turns" {
  description = "CLAUDE_MAX_TURNS variable value"
  value       = github_actions_variable.claude_max_turns.value
}

# --- AWS デプロイ関連 ---

output "aws_role_arn_created_at" {
  description = "AWS_ROLE_ARN secret creation timestamp"
  value       = github_actions_secret.aws_role_arn.created_at
}

output "aws_region" {
  description = "AWS_REGION variable value"
  value       = github_actions_variable.aws_region.value
}

output "cloudfront_distribution_id" {
  description = "CLOUDFRONT_DISTRIBUTION_ID variable value"
  value       = github_actions_variable.cloudfront_distribution_id.value
}

output "ecr_repository_url" {
  description = "ECR_REPOSITORY_URL variable value"
  value       = github_actions_variable.ecr_repository_url.value
}

output "lambda_function_name" {
  description = "LAMBDA_FUNCTION_NAME variable value"
  value       = github_actions_variable.lambda_function_name.value
}

output "next_public_api_url" {
  description = "NEXT_PUBLIC_API_URL variable value"
  value       = github_actions_variable.next_public_api_url.value
}

output "s3_bucket_name" {
  description = "S3_BUCKET_NAME variable value"
  value       = github_actions_variable.s3_bucket_name.value
}
