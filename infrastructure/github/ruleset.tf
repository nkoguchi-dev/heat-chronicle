# --- Default branch protection ---

resource "github_repository_ruleset" "protect_main" {
  name        = "Protect main"
  repository  = var.github_repository
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  rules {
    non_fast_forward = true

    pull_request {
      allowed_merge_methods             = ["merge", "squash", "rebase"]
      dismiss_stale_reviews_on_push     = false
      require_code_owner_review         = false
      require_last_push_approval        = false
      required_approving_review_count   = 0
      required_review_thread_resolution = false
    }

    required_status_checks {
      strict_required_status_checks_policy = false

      required_check {
        context = "Frontend quality checks"
      }

      required_check {
        context = "Backend lint and unit tests"
      }

      required_check {
        context = "Backend integration tests"
      }

      required_check {
        context = "Browser smoke tests"
      }
    }
  }
}
