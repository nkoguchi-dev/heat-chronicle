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
