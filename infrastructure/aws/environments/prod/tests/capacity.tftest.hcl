# Offline plan tests. These mocks do not validate AWS behavior or live state.
mock_provider "aws" {
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
  system_name      = "capacity-test"
  environment      = "test"
  aws_region       = "ap-northeast-1"
  domain_name      = "example.test"
  api_domain_name  = "api.example.test"
  hosted_zone_name = "example.test"
  api_capacity = {
    stage_rate                  = 5
    stage_burst                 = 10
    fetch_month_rate            = 1
    fetch_month_burst           = 2
    lambda_reserved_concurrency = 5
  }
}

run "agreed_capacity" {
  command = plan
  module { source = "../../modules/backend_api" }

  assert {
    condition = (
      aws_apigatewayv2_stage.default.default_route_settings[0].throttling_rate_limit == 5 &&
      aws_apigatewayv2_stage.default.default_route_settings[0].throttling_burst_limit == 10 &&
      one(aws_apigatewayv2_stage.default.route_settings).throttling_rate_limit == 1 &&
      one(aws_apigatewayv2_stage.default.route_settings).throttling_burst_limit == 2 &&
      one(aws_apigatewayv2_stage.default.route_settings).route_key == aws_apigatewayv2_route.fetch_month.route_key
    )
    error_message = "The stage fallback and explicit monthly route must enforce the agreed separate limits."
  }
  assert {
    condition = (
      aws_apigatewayv2_route.fetch_month.route_key == "GET /api/temperature/{station_id}/fetch-month" &&
      aws_apigatewayv2_route.fetch_month.target == aws_apigatewayv2_route.default.target &&
      aws_lambda_function.backend.reserved_concurrent_executions == 5 &&
      contains(one(aws_apigatewayv2_api.backend.cors_configuration).expose_headers, "Retry-After")
    )
    error_message = "Monthly requests must use the existing integration, bounded Lambda and exposed retry header."
  }
}

run "reject_zero_concurrency" {
  command = plan
  module { source = "../../modules/backend_api" }
  variables {
    api_capacity = {
      stage_rate = 5, stage_burst = 10, fetch_month_rate = 1, fetch_month_burst = 2, lambda_reserved_concurrency = 0
    }
  }
  expect_failures = [var.api_capacity]
}

run "reject_monthly_above_stage" {
  command = plan
  module { source = "../../modules/backend_api" }
  variables {
    api_capacity = {
      stage_rate = 5, stage_burst = 10, fetch_month_rate = 6, fetch_month_burst = 2, lambda_reserved_concurrency = 5
    }
  }
  expect_failures = [var.api_capacity]
}

run "reject_fractional_burst" {
  command = plan
  module { source = "../../modules/backend_api" }
  variables {
    api_capacity = {
      stage_rate = 5, stage_burst = 10, fetch_month_rate = 1, fetch_month_burst = 1.5, lambda_reserved_concurrency = 5
    }
  }
  expect_failures = [var.api_capacity]
}
