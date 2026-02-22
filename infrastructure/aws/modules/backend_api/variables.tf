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
