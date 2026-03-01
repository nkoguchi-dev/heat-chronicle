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
