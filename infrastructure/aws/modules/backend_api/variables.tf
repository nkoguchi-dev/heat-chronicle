variable "system_name" {
  description = "System name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. prod, dev)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "domain_name" {
  description = "Frontend domain name (used for CORS)"
  type        = string
}

variable "api_domain_name" {
  description = "Custom domain name for the API (e.g. api.heat-chronicle.koppepan.org)"
  type        = string
}

variable "hosted_zone_name" {
  description = "Route 53 hosted zone name (e.g. koppepan.org)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
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
  validation {
    condition = (
      var.api_capacity.stage_rate > 0 &&
      var.api_capacity.fetch_month_rate > 0 &&
      var.api_capacity.fetch_month_rate <= var.api_capacity.stage_rate &&
      var.api_capacity.stage_burst >= 1 &&
      floor(var.api_capacity.stage_burst) == var.api_capacity.stage_burst &&
      var.api_capacity.fetch_month_burst >= 1 &&
      floor(var.api_capacity.fetch_month_burst) == var.api_capacity.fetch_month_burst &&
      var.api_capacity.fetch_month_burst <= var.api_capacity.stage_burst &&
      var.api_capacity.lambda_reserved_concurrency >= 1 &&
      floor(var.api_capacity.lambda_reserved_concurrency) == var.api_capacity.lambda_reserved_concurrency
    )
    error_message = "Rates must be positive; bursts and reserved concurrency must be positive integers. Monthly limits must not exceed stage limits."
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
