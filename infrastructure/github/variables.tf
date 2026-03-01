variable "github_repository" {
  description = "GitHub repository name"
  type        = string
  default     = "heat-chronicle"
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude PR review (sk-ant-...)"
  type        = string
  sensitive   = true
}

variable "claude_max_turns" {
  description = "Maximum turns for Claude PR review"
  type        = number
  default     = 20
}

# --- AWS デプロイ関連 ---

variable "aws_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC deploy"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-northeast-1"
}

variable "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for backend Docker images"
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name for backend"
  type        = string
}

variable "next_public_api_url" {
  description = "Public API URL for frontend"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for frontend deployment"
  type        = string
}
