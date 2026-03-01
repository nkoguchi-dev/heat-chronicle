output "anthropic_api_key_created_at" {
  description = "ANTHROPIC_API_KEY secret creation timestamp"
  value       = github_actions_secret.anthropic_api_key.created_at
}

output "claude_max_turns" {
  description = "CLAUDE_MAX_TURNS variable value"
  value       = github_actions_variable.claude_max_turns.value
}
