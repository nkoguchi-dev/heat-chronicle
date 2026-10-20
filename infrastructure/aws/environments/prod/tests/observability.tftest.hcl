mock_provider "aws" {
  mock_resource "aws_iam_policy" {
    defaults = { arn = "arn:aws:iam::123456789012:policy/test-lambda-logs" }
  }
  override_resource {
    target = aws_apigatewayv2_api.backend
    values = {
      id            = "test-api"
      execution_arn = "arn:aws:execute-api:ap-northeast-1:123456789012:test-api"
      arn           = "arn:aws:apigateway:ap-northeast-1::/apis/test-api"
    }
    override_during = plan
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

run "safe_access_log_and_alarms" {
  command = plan
  module { source = "../../modules/backend_api" }
  assert {
    condition = (
      aws_cloudwatch_log_group.api_access.retention_in_days == 14 &&
      one(aws_apigatewayv2_stage.default.access_log_settings).destination_arn == aws_cloudwatch_log_group.api_access.arn &&
      toset(keys(jsondecode(one(aws_apigatewayv2_stage.default.access_log_settings).format))) == toset([
        "request_id", "request_time_epoch", "route_key", "status", "integration_status",
        "lambda_service_status", "response_latency_ms", "integration_latency_ms", "response_length"
      ]) &&
      jsondecode(one(aws_apigatewayv2_stage.default.access_log_settings).format).route_key == "$context.routeKey"
    )
    error_message = "Access logs must use an explicit safe field allowlist and bounded retention."
  }
  assert {
    condition = (
      length(aws_cloudwatch_metric_alarm.api) == 2 &&
      length(aws_cloudwatch_metric_alarm.lambda) == 2 &&
      aws_cloudwatch_metric_alarm.api["server_errors"].metric_name == "5xx" &&
      aws_cloudwatch_metric_alarm.api["server_errors"].dimensions == tomap({
        ApiId = aws_apigatewayv2_api.backend.id, Stage = "$default"
      }) &&
      aws_cloudwatch_metric_alarm.lambda["throttles"].dimensions == tomap({ FunctionName = aws_lambda_function.backend.function_name }) &&
      aws_cloudwatch_metric_alarm.api_throttles.namespace == "capacity-test/test/API" &&
      aws_cloudwatch_log_metric_filter.api_throttles.pattern == "{ $.status = \"429\" }"
    )
    error_message = "Use HTTP API stage dimensions, Lambda function dimensions, and a dedicated 429 filter."
  }
  assert {
    condition = alltrue(concat(
      [for alarm in aws_cloudwatch_metric_alarm.api : alarm.actions_enabled && alarm.treat_missing_data == "notBreaching" && alarm.period == 300 && alarm.alarm_actions == toset([aws_sns_topic.api_alerts.arn]) && alarm.ok_actions == alarm.alarm_actions && length(alarm.insufficient_data_actions) == 0],
      [for alarm in aws_cloudwatch_metric_alarm.lambda : alarm.actions_enabled && alarm.treat_missing_data == "notBreaching" && alarm.period == 300 && alarm.alarm_actions == toset([aws_sns_topic.api_alerts.arn]) && alarm.ok_actions == alarm.alarm_actions && length(alarm.insufficient_data_actions) == 0],
      [aws_cloudwatch_metric_alarm.api_throttles.datapoints_to_alarm == 2 && aws_cloudwatch_metric_alarm.api_throttles.evaluation_periods == 3 && aws_cloudwatch_metric_alarm.api_throttles.threshold == 10]
    ))
    error_message = "Use bounded evaluation windows and transition-only alarm/recovery notifications."
  }
  assert {
    condition = (
      aws_sns_topic_subscription.discord_alerts.protocol == "lambda" &&
      length(jsondecode(aws_sns_topic_policy.api_alerts.policy).Statement) == 1 &&
      jsondecode(aws_sns_topic_policy.api_alerts.policy).Statement[0].Action == "sns:Publish" &&
      jsondecode(aws_sns_topic_policy.api_alerts.policy).Statement[0].Principal.Service == "cloudwatch.amazonaws.com" &&
      jsondecode(aws_sns_topic_policy.api_alerts.policy).Statement[0].Condition.StringEquals["aws:SourceAccount"] == "123456789012" &&
      jsondecode(aws_sns_topic_policy.api_alerts.policy).Statement[0].Condition.ArnLike["aws:SourceArn"] == "arn:aws:cloudwatch:ap-northeast-1:123456789012:alarm:capacity-test-test-*"
    )
    error_message = "Use the application relay and do not allow other accounts/applications to publish."
  }
}


run "discord_delivery_boundary" {
  command = plan
  module { source = "../../modules/backend_api" }
  assert {
    condition = (
      aws_ssm_parameter.discord_webhook.type == "SecureString" &&
      aws_ssm_parameter.discord_webhook.tier == "Standard" &&
      aws_ssm_parameter.discord_webhook.key_id == "alias/aws/ssm" &&
      aws_ssm_parameter.discord_webhook.value_wo_version == 1 &&
      aws_lambda_function.discord_alerts.reserved_concurrent_executions == 1 &&
      aws_lambda_function.discord_alerts.timeout == 15 &&
      toset(keys(aws_lambda_function.discord_alerts.environment[0].variables)) == toset([
        "WEBHOOK_PARAMETER_NAME", "EXPECTED_TOPIC_ARN", "ALARM_ARN_PREFIX", "ALARM_NAMES"
      ]) &&
      aws_lambda_permission.discord_alerts.source_arn == aws_sns_topic.api_alerts.arn &&
      aws_lambda_permission.discord_alerts.source_account == "123456789012" &&
      aws_lambda_permission.discord_alerts.principal == "sns.amazonaws.com"
    )
    error_message = "Webhook values must stay outside plan/state and the invocation boundary must be restricted to this topic/account."
  }
  assert {
    condition = (
      aws_cloudwatch_log_group.discord_alerts.retention_in_days == 14 &&
      aws_sqs_queue.notification_failures.message_retention_seconds == 1209600 &&
      aws_sqs_queue.notification_failures.sqs_managed_sse_enabled &&
      aws_lambda_function_event_invoke_config.discord_alerts.maximum_retry_attempts == 2 &&
      aws_lambda_function_event_invoke_config.discord_alerts.maximum_event_age_in_seconds == 3600 &&
      aws_lambda_function.discord_alerts.dead_letter_config[0].target_arn == aws_sqs_queue.notification_failures.arn &&
      jsondecode(aws_sns_topic_subscription.discord_alerts.redrive_policy).deadLetterTargetArn == aws_sqs_queue.notification_failures.arn &&
      length(aws_cloudwatch_metric_alarm.notification_failures.alarm_actions) == 0
    )
    error_message = "Bound retries and retention, retain both SNS/Lambda delivery failures, and do not create a recursive alarm loop."
  }
  assert {
    condition = (
      jsondecode(aws_iam_role_policy.discord_alerts.policy).Statement[1].Action == "ssm:GetParameter" &&
      jsondecode(aws_iam_role_policy.discord_alerts.policy).Statement[1].Resource == aws_ssm_parameter.discord_webhook.arn &&
      jsondecode(aws_iam_role_policy.discord_alerts.policy).Statement[2].Action == "sqs:SendMessage" &&
      jsondecode(aws_sqs_queue_policy.notification_failures.policy).Statement[0].Condition.ArnEquals["aws:SourceArn"] == aws_sns_topic.api_alerts.arn
    )
    error_message = "Limit secret access and failure queue writes to the application resources."
  }
}

run "reject_invalid_webhook" {
  command = plan
  module { source = "../../modules/backend_api" }
  variables { discord_webhook_url = "https://evil.test/api/webhooks/123/token" }
  expect_failures = [var.discord_webhook_url]
}

run "reject_invalid_webhook_version" {
  command = plan
  module { source = "../../modules/backend_api" }
  variables { discord_webhook_version = 0 }
  expect_failures = [var.discord_webhook_version]
}

run "rotate_write_only_webhook" {
  command = plan
  module { source = "../../modules/backend_api" }
  variables { discord_webhook_version = 2 }
  assert {
    condition     = aws_ssm_parameter.discord_webhook.value_wo_version == 2
    error_message = "Webhook rotation must use an explicit write-only version."
  }
}
