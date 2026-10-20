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

variable "domain_name" {
  description = "Custom domain name for the frontend"
  type        = string
  default     = "heat-chronicle.koppepan.org"
}

variable "hosted_zone_name" {
  description = "Route 53 hosted zone name"
  type        = string
  default     = "koppepan.org"
}

variable "api_domain_name" {
  description = "Custom domain name for the backend API"
  type        = string
  default     = "api.heat-chronicle.koppepan.org"
}

variable "api_capacity" {
  description = "Public API capacity agreed in docs/API_PROTECTION.md; account headroom must be checked before applying"
  type = object({
    stage_rate                  = number
    stage_burst                 = number
    fetch_month_rate            = number
    fetch_month_burst           = number
    lambda_reserved_concurrency = number
  })
  default = {
    stage_rate                  = 5
    stage_burst                 = 10
    fetch_month_rate            = 1
    fetch_month_burst           = 2
    lambda_reserved_concurrency = 5
  }
}

variable "discord_webhook_url" {
  description = "Discord incoming webhook URL; persist only in SOPS-encrypted tfvars, never in state or plan"
  type        = string
  sensitive   = true
  ephemeral   = true
  nullable    = false
  validation {
    condition     = can(regex("^https://discord\\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+$", var.discord_webhook_url))
    error_message = "Provide a Discord incoming webhook URL without query parameters or a fragment."
  }
}

variable "discord_webhook_version" {
  description = "Increment whenever the encrypted webhook URL changes; write-only values cannot be compared for drift"
  type        = number
  default     = 1
  validation {
    condition     = var.discord_webhook_version >= 1 && floor(var.discord_webhook_version) == var.discord_webhook_version
    error_message = "Webhook version must be a positive integer."
  }
}
