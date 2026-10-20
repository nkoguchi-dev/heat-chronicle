mock_provider "aws" {}

variables {
  test_id = "issue5-mock"
}

run "isolated_capacity_fixture" {
  command = plan
  assert {
    condition     = aws_lambda_function.fixture.reserved_concurrent_executions == 5 && aws_lambda_function.fixture.timeout == 10
    error_message = "Fixture must bound concurrent work and duration."
  }
  assert {
    condition     = aws_apigatewayv2_stage.fixture.default_route_settings[0].throttling_rate_limit == 5 && one(aws_apigatewayv2_stage.fixture.route_settings).throttling_rate_limit == 1
    error_message = "Keep stage and month route aligned with adopted capacity."
  }
  assert {
    condition     = aws_cloudwatch_log_group.fixture.retention_in_days == 1
    error_message = "Do not retain temporary fixture logs indefinitely."
  }
}
