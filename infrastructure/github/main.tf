# Claude PR レビュー用 Anthropic API キー
resource "github_actions_secret" "anthropic_api_key" {
  repository      = var.github_repository
  secret_name     = "ANTHROPIC_API_KEY"
  plaintext_value = var.anthropic_api_key
}

# Claude の最大ターン数
resource "github_actions_variable" "claude_max_turns" {
  repository    = var.github_repository
  variable_name = "CLAUDE_MAX_TURNS"
  value         = tostring(var.claude_max_turns)
}
