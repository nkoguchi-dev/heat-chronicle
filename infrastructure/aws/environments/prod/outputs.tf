output "cloudfront_distribution_domain" {
  description = "CloudFront distribution domain name for site access"
  value       = module.static_site.cloudfront_distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation"
  value       = module.static_site.cloudfront_distribution_id
}

output "s3_bucket_name" {
  description = "S3 bucket name for deployment"
  value       = module.static_site.s3_bucket_name
}

output "github_actions_deploy_role_arn" {
  description = "IAM role ARN for GitHub Actions deploy"
  value       = aws_iam_role.github_actions_deploy.arn
}

output "site_url" {
  description = "Site URL with custom domain"
  value       = module.static_site.site_url
}

output "ecr_repository_url" {
  description = "ECR repository URL for backend images"
  value       = module.backend_api.ecr_repository_url
}

output "lambda_function_name" {
  description = "Lambda function name for backend"
  value       = module.backend_api.lambda_function_name
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = module.backend_api.api_gateway_url
}

output "api_domain_url" {
  description = "API custom domain URL"
  value       = module.backend_api.api_domain_url
}
