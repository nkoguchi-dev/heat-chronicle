# Offline plan tests. These mocks do not validate AWS behavior or live state.
mock_provider "aws" {
  mock_resource "aws_iam_policy" {
    defaults = { arn = "arn:aws:iam::123456789012:policy/test-lambda-logs" }
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
  override_during = plan
  override_resource {
    target          = aws_apigatewayv2_integration.backend
    values          = { id = "test-integration" }
    override_during = plan
  }
  mock_resource "aws_acm_certificate" {
    defaults = {
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

variables {
  discord_webhook_url = "https://discord.com/api/webhooks/123/offline_test_only"
  system_name         = "capacity-test"
  environment         = "test"
  aws_region          = "ap-northeast-1"
  domain_name         = "example.test"
  api_domain_name     = "api.example.test"
  hosted_zone_name    = "example.test"
  api_capacity = {
    stage_rate                  = 5
    stage_burst                 = 10
    fetch_month_rate            = 1
    fetch_month_burst           = 2
    lambda_reserved_concurrency = 5
  }
}

run "only_backend_image_retrieval" {
  command = plan
  module { source = "../../modules/backend_api" }
  assert {
    condition = (
      aws_ecr_repository_policy.backend.repository == aws_ecr_repository.backend.name &&
      jsondecode(aws_ecr_repository_policy.backend.policy).Version == "2012-10-17" &&
      length(jsondecode(aws_ecr_repository_policy.backend.policy).Statement) == 1 &&
      jsondecode(aws_ecr_repository_policy.backend.policy).Statement[0].Effect == "Allow" &&
      jsondecode(aws_ecr_repository_policy.backend.policy).Statement[0].Principal == { Service = "lambda.amazonaws.com" } &&
      toset(jsondecode(aws_ecr_repository_policy.backend.policy).Statement[0].Action) == toset(["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]) &&
      jsondecode(aws_ecr_repository_policy.backend.policy).Statement[0].Condition == {
        ArnEquals = { "aws:SourceArn" = "arn:aws:lambda:ap-northeast-1:123456789012:function:capacity-test-test-backend" }
      }
    )
    error_message = "The existing repository must grant only image retrieval to Lambda for this exact backend function, with no policy management operations."
  }
}
