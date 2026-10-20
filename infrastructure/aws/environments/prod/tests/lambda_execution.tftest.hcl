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

override_resource {
  target          = aws_dynamodb_table.stations
  override_during = plan
  values = {
    id  = "capacity-test-test-stations"
    arn = "arn:aws:dynamodb:ap-northeast-1:123456789012:table/capacity-test-test-stations"
  }
}
override_resource {
  target          = aws_dynamodb_table.daily_temperature
  override_during = plan
  values = {
    id  = "capacity-test-test-daily-temperature"
    arn = "arn:aws:dynamodb:ap-northeast-1:123456789012:table/capacity-test-test-daily-temperature"
  }
}
override_resource {
  target          = aws_dynamodb_table.fetch_log
  override_during = plan
  values = {
    id  = "capacity-test-test-fetch-log"
    arn = "arn:aws:dynamodb:ap-northeast-1:123456789012:table/capacity-test-test-fetch-log"
  }
}
override_resource {
  target          = aws_dynamodb_table.scrape_jobs
  override_during = plan
  values = {
    id  = "capacity-test-test-scrape-jobs"
    arn = "arn:aws:dynamodb:ap-northeast-1:123456789012:table/capacity-test-test-scrape-jobs"
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

run "table_operations_follow_current_call_sites" {
  command = plan
  module { source = "../../modules/backend_api" }
  assert {
    condition = (
      length(jsondecode(aws_iam_role_policy.lambda_dynamodb.policy).Statement) == 5 &&
      alltrue([for s in jsondecode(aws_iam_role_policy.lambda_dynamodb.policy).Statement : s.Effect == "Allow"]) &&
      { for s in jsondecode(aws_iam_role_policy.lambda_dynamodb.policy).Statement : s.Sid => {
        actions = toset(s.Action), resources = toset(s.Resource)
        } } == {
        StationRead = {
          actions = toset(["dynamodb:GetItem", "dynamodb:Scan"]), resources = toset([aws_dynamodb_table.stations.arn])
        }
        StationIndexQuery = {
          actions = toset(["dynamodb:Query"]), resources = toset([aws_dynamodb_table.stations.arn, "${aws_dynamodb_table.stations.arn}/index/prec_no-index"])
        }
        StationMigrations = {
          actions = toset(["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:BatchWriteItem"]), resources = toset([aws_dynamodb_table.stations.arn])
        }
        TemperatureData = {
          actions = toset(["dynamodb:Query", "dynamodb:BatchWriteItem"]), resources = toset([aws_dynamodb_table.daily_temperature.arn])
        }
        FetchLogAndLease = {
          actions = toset(["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]), resources = toset([aws_dynamodb_table.fetch_log.arn])
        }
      }
    )
    error_message = "Grant only the current per-table operations and named station index, including cold-start migrations and the shared fetch lease."
  }
  assert {
    condition = (
      length(jsondecode(aws_iam_policy.lambda_logs.policy).Statement) == 1 &&
      jsondecode(aws_iam_policy.lambda_logs.policy).Statement[0].Effect == "Allow" &&
      toset(jsondecode(aws_iam_policy.lambda_logs.policy).Statement[0].Action) == toset(["logs:CreateLogStream", "logs:PutLogEvents"]) &&
      jsondecode(aws_iam_policy.lambda_logs.policy).Statement[0].Resource == "${aws_cloudwatch_log_group.lambda.arn}:*" &&
      aws_iam_role_policy_attachment.lambda_logs.policy_arn == aws_iam_policy.lambda_logs.arn &&
      aws_iam_role_policy_attachment.lambda_logs.role == aws_iam_role.lambda_execution.name
    )
    error_message = "The execution role must attach only the precreated function log group's stream write policy."
  }
}
