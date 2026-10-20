# Inspect the real policy-document inputs. Mocked JSON does not prove role wiring,
# provider rendering or AWS IAM evaluation; inspect the real plan separately.
mock_provider "aws" {
  mock_resource "aws_iam_policy" {
    defaults = { arn = "arn:aws:iam::123456789012:policy/test-lambda-logs" }
  }
  override_during = plan
  mock_resource "aws_iam_openid_connect_provider" {
    defaults = { arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{}" }
  }
  override_resource {
    target = module.backend_api.aws_apigatewayv2_api.backend
    values = {
      id            = "test-api"
      execution_arn = "arn:aws:execute-api:ap-northeast-1:123456789012:test-api"
      arn           = "arn:aws:apigateway:ap-northeast-1::/apis/test-api"
    }
  }
  mock_resource "aws_sqs_queue" {
    defaults = { arn = "arn:aws:sqs:ap-northeast-1:123456789012:test-failures", url = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/test-failures" }
  }
  mock_resource "aws_ssm_parameter" {
    defaults = { arn = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/test/discord-webhook" }
  }
  mock_resource "aws_lambda_function" {
    defaults = { arn = "arn:aws:lambda:ap-northeast-1:123456789012:function:test-relay" }
  }
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:ap-northeast-1:123456789012:test-alerts" }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-northeast-1:123456789012:log-group:/test" }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  override_resource {
    target = module.backend_api.aws_apigatewayv2_integration.backend
    values = { id = "test-integration" }
  }
  mock_resource "aws_acm_certificate" {
    override_during = plan
    defaults = {
      id  = "test-api-certificate"
      arn = "arn:aws:acm:ap-northeast-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
      domain_validation_options = [{
        domain_name           = "api.example.test"
        resource_record_name  = "_validation.api.example.test"
        resource_record_type  = "CNAME"
        resource_record_value = "validation.example.test"
      }]
    }
  }

  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/test-lambda" }
  }
}
mock_provider "aws" {
  alias = "us_east_1"
}

# Isolate the static site and mock all backend resources, including the adopted
# ECR policy. No AWS calls, deployments, secret reads or notifications occur.
override_module {
  target = module.static_site
  outputs = {
    s3_bucket_name                      = "test-frontend"
    s3_bucket_arn                       = "arn:aws:s3:::test-frontend"
    cloudfront_distribution_id          = "TEST"
    cloudfront_distribution_arn         = "arn:aws:cloudfront::123456789012:distribution/TEST"
    cloudfront_distribution_domain_name = "example.cloudfront.net"
    site_url                            = "https://example.test"
  }
}
override_resource {
  target = module.backend_api.aws_ecr_repository_policy.backend
  values = {
    id          = "heat-chronicle-prod-backend"
    repository  = "heat-chronicle-prod-backend"
    registry_id = "123456789012"
    policy      = "{}"
  }
}
variables {
  discord_webhook_url = "https://discord.com/api/webhooks/123/offline_test_only"
}

run "only_public_release_branch_can_deploy" {
  command = plan
  assert {
    condition = (
      length(data.aws_iam_policy_document.github_actions_assume_role.statement) == 1 &&
      one(data.aws_iam_policy_document.github_actions_assume_role.statement).effect == "Allow" &&
      toset(one(data.aws_iam_policy_document.github_actions_assume_role.statement).actions) == toset(["sts:AssumeRoleWithWebIdentity"]) &&
      length(one(data.aws_iam_policy_document.github_actions_assume_role.statement).principals) == 1 &&
      one(one(data.aws_iam_policy_document.github_actions_assume_role.statement).principals).type == "Federated" &&
      toset(one(one(data.aws_iam_policy_document.github_actions_assume_role.statement).principals).identifiers) == toset([aws_iam_openid_connect_provider.github_actions.arn]) &&
      length(one(data.aws_iam_policy_document.github_actions_assume_role.statement).condition) == 2 &&
      alltrue([for c in one(data.aws_iam_policy_document.github_actions_assume_role.statement).condition : c.test == "StringEquals"]) &&
      tomap({ for c in one(data.aws_iam_policy_document.github_actions_assume_role.statement).condition : c.variable => toset(c.values) }) == tomap({
        "token.actions.githubusercontent.com:aud" = toset(["sts.amazonaws.com"])
        "token.actions.githubusercontent.com:sub" = toset(["repo:nkoguchi-dev/heat-chronicle:ref:refs/heads/release/prod"])
      })
    )
    error_message = "Allow only the GitHub OIDC provider, STS audience and existing public release/prod branch using exact conditions."
  }
  assert {
    condition = alltrue([
      for subject in [
        "repo:nkoguchi-dev/heat-chronicle:ref:refs/heads/main",
        "repo:nkoguchi-dev/heat-chronicle:ref:refs/heads/feature/test",
        "repo:nkoguchi-dev/heat-chronicle:ref:refs/heads/release/prod-extra",
        "repo:nkoguchi-dev/heat-chronicle:ref:refs/tags/release/prod",
        "repo:nkoguchi-dev/heat-chronicle:pull_request",
        "repo:nkoguchi-dev/heat-chronicle:environment:production",
        "repo:nkoguchi-dev/other-repository:ref:refs/heads/release/prod",
        "repo:other-owner/heat-chronicle:ref:refs/heads/release/prod",
        ""
        ] : alltrue([
          for c in one(data.aws_iam_policy_document.github_actions_assume_role.statement).condition :
          !contains(c.values, subject) if c.variable == "token.actions.githubusercontent.com:sub"
      ])
    ])
    error_message = "Non-release refs, PRs, environments, other repositories and empty subjects must not match the exact subject allowlist."
  }
}
