# --- Dependency security ---

resource "github_repository_vulnerability_alerts" "dependabot" {
  repository = var.github_repository
  enabled    = true
}

resource "github_repository_dependabot_security_updates" "dependabot" {
  repository = var.github_repository
  enabled    = true

  depends_on = [github_repository_vulnerability_alerts.dependabot]
}
