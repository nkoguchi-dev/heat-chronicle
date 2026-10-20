# Infrastructure telemetry deliberately omits request bodies, query strings,
# source IPs, user agents, headers and exception messages.
data "aws_caller_identity" "observability" {}
data "aws_partition" "observability" {}

locals {
  alarm_topic_arn = aws_sns_topic.api_alerts.arn
  api_alarm_definitions = {
    server_errors = {
      metric_name        = "5xx", statistic = "Sum", threshold = 5,
      evaluation_periods = 1, datapoints_to_alarm = 1
    }
    latency = {
      metric_name        = "Latency", statistic = "Maximum", threshold = 25000,
      evaluation_periods = 3, datapoints_to_alarm = 2
    }
  }
  lambda_alarm_definitions = {
    errors = {
      metric_name        = "Errors", threshold = 1,
      evaluation_periods = 1, datapoints_to_alarm = 1
    }
    throttles = {
      metric_name        = "Throttles", threshold = 5,
      evaluation_periods = 3, datapoints_to_alarm = 2
    }
  }
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/vendedlogs/apigateway/${local.prefix}"
  retention_in_days = 14
  tags              = var.tags
}

resource "aws_cloudwatch_log_metric_filter" "api_throttles" {
  name           = "${local.prefix}-http-429"
  log_group_name = aws_cloudwatch_log_group.api_access.name
  pattern        = "{ $.status = \"429\" }"

  metric_transformation {
    name          = "GatewayThrottles"
    namespace     = "${var.system_name}/${var.environment}/API"
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}

resource "aws_sns_topic" "api_alerts" {
  name = "${local.prefix}-api-alerts"
  tags = var.tags
}

resource "aws_sns_topic_policy" "api_alerts" {
  arn = local.alarm_topic_arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowApplicationCloudWatchAlarms"
      Effect    = "Allow"
      Principal = { Service = "cloudwatch.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = local.alarm_topic_arn
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.observability.account_id }
        ArnLike = {
          "aws:SourceArn" = "arn:${data.aws_partition.observability.partition}:cloudwatch:${var.aws_region}:${data.aws_caller_identity.observability.account_id}:alarm:${local.prefix}-*"
        }
      }
    }]
  })
}

resource "aws_cloudwatch_metric_alarm" "api" {
  depends_on          = [aws_sns_topic_policy.api_alerts]
  actions_enabled     = true
  for_each            = local.api_alarm_definitions
  alarm_name          = "${local.prefix}-api-${replace(each.key, "_", "-")}"
  alarm_description   = "See infrastructure/docs/api-observability.md; traffic-based signal, not an availability guarantee."
  namespace           = "AWS/ApiGateway"
  metric_name         = each.value.metric_name
  statistic           = each.value.statistic
  period              = 300
  evaluation_periods  = each.value.evaluation_periods
  datapoints_to_alarm = each.value.datapoints_to_alarm
  threshold           = each.value.threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions = {
    ApiId = aws_apigatewayv2_api.backend.id
    Stage = aws_apigatewayv2_stage.default.name
  }
  alarm_actions             = [local.alarm_topic_arn]
  ok_actions                = [local.alarm_topic_arn]
  insufficient_data_actions = []
  tags                      = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda" {
  depends_on                = [aws_sns_topic_policy.api_alerts]
  actions_enabled           = true
  for_each                  = local.lambda_alarm_definitions
  alarm_name                = "${local.prefix}-lambda-${each.key}"
  alarm_description         = "See infrastructure/docs/api-observability.md; HTTP 503 is not necessarily a Lambda function error."
  namespace                 = "AWS/Lambda"
  metric_name               = each.value.metric_name
  statistic                 = "Sum"
  period                    = 300
  evaluation_periods        = each.value.evaluation_periods
  datapoints_to_alarm       = each.value.datapoints_to_alarm
  threshold                 = each.value.threshold
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  treat_missing_data        = "notBreaching"
  dimensions                = { FunctionName = aws_lambda_function.backend.function_name }
  alarm_actions             = [local.alarm_topic_arn]
  ok_actions                = [local.alarm_topic_arn]
  insufficient_data_actions = []
  tags                      = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_throttles" {
  depends_on                = [aws_sns_topic_policy.api_alerts]
  actions_enabled           = true
  alarm_name                = "${local.prefix}-api-throttles"
  alarm_description         = "Sustained HTTP 429; inspect API access logs. See infrastructure/docs/api-observability.md."
  namespace                 = "${var.system_name}/${var.environment}/API"
  metric_name               = "GatewayThrottles"
  statistic                 = "Sum"
  period                    = 300
  evaluation_periods        = 3
  datapoints_to_alarm       = 2
  threshold                 = 10
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  treat_missing_data        = "notBreaching"
  alarm_actions             = [local.alarm_topic_arn]
  ok_actions                = [local.alarm_topic_arn]
  insufficient_data_actions = []
  tags                      = var.tags
}
