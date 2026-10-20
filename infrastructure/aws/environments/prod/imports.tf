# Adopt the existing policy in the same root that owns this ECR repository.
# Review the import + policy update together; do not run an imperative import.
import {
  to = module.backend_api.aws_ecr_repository_policy.backend
  id = "${var.system_name}-${var.environment}-backend"
}
