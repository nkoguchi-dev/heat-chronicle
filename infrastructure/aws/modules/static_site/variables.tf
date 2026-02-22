variable "system_name" {
  description = "System name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. prod, dev)"
  type        = string
}

variable "default_root_object" {
  description = "Default root object for CloudFront distribution"
  type        = string
  default     = "index.html"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
