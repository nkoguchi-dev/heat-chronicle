variable "system_name" {
  description = "System name used for resource naming"
  type        = string
  default     = "heat-chronicle"
}

variable "environment" {
  description = "Environment name (e.g. prod, dev)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "github_repository" {
  description = "GitHub repository for OIDC (owner/repo format)"
  type        = string
  default     = "nkoguchi-dev/heat-chronicle"
}
