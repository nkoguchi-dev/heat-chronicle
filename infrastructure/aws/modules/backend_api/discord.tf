# Ephemeral input + write-only argument: the URL is never persisted in plan/state.
resource "aws_ssm_parameter" "discord_webhook" {
  name             = "/${local.prefix}/discord-webhook"
  description      = "Discord incoming webhook URL for API alarm notifications"
  type             = "SecureString"
  tier             = "Standard"
  key_id           = "alias/aws/ssm"
  value_wo         = var.discord_webhook_url
  value_wo_version = var.discord_webhook_version
  tags             = var.tags
}

resource "aws_sqs_queue" "notification_failures" {
  name                      = "${local.prefix}-notification-failures"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = var.tags
}

resource "aws_sqs_queue_policy" "notification_failures" {
  queue_url = aws_sqs_queue.notification_failures.url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.notification_failures.arn
      Condition = {
        ArnEquals    = { "aws:SourceArn" = local.alarm_topic_arn }
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.observability.account_id }
      }
    }]
  })
}

resource "aws_cloudwatch_log_group" "discord_alerts" {
  name              = "/aws/lambda/${local.prefix}-discord-alerts"
  retention_in_days = 14
  tags              = var.tags
}

resource "aws_iam_role" "discord_alerts" {
  name = "${local.prefix}-discord-alerts"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Action = "sts:AssumeRole",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "discord_alerts" {
  name = "${local.prefix}-discord-alerts"
  role = aws_iam_role.discord_alerts.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
        Resource = "${aws_cloudwatch_log_group.discord_alerts.arn}:*"
      },
      {
        Effect   = "Allow", Action = "ssm:GetParameter",
        Resource = aws_ssm_parameter.discord_webhook.arn
      },
      {
        Effect   = "Allow", Action = "sqs:SendMessage",
        Resource = aws_sqs_queue.notification_failures.arn
      }
    ]
  })
}

resource "aws_lambda_function" "discord_alerts" {
  depends_on                     = [aws_iam_role_policy.discord_alerts]
  function_name                  = "${local.prefix}-discord-alerts"
  role                           = aws_iam_role.discord_alerts.arn
  runtime                        = "python3.13"
  handler                        = "relay.handler"
  filename                       = "${path.module}/discord/relay.zip"
  source_code_hash               = filebase64sha256("${path.module}/discord/relay.zip")
  timeout                        = 15
  memory_size                    = 128
  reserved_concurrent_executions = 1
  environment {
    variables = {
      WEBHOOK_PARAMETER_NAME = aws_ssm_parameter.discord_webhook.name
      EXPECTED_TOPIC_ARN     = local.alarm_topic_arn
      ALARM_ARN_PREFIX       = "arn:${data.aws_partition.observability.partition}:cloudwatch:${var.aws_region}:${data.aws_caller_identity.observability.account_id}:alarm:"
      ALARM_NAMES = jsonencode(concat(
        [for alarm in aws_cloudwatch_metric_alarm.api : alarm.alarm_name],
        [for alarm in aws_cloudwatch_metric_alarm.lambda : alarm.alarm_name],
        [aws_cloudwatch_metric_alarm.api_throttles.alarm_name]
      ))
    }
  }
  dead_letter_config {
    target_arn = aws_sqs_queue.notification_failures.arn
  }
  tags = var.tags
}

resource "aws_lambda_function_event_invoke_config" "discord_alerts" {
  function_name                = aws_lambda_function.discord_alerts.function_name
  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2
}

resource "aws_lambda_permission" "discord_alerts" {
  statement_id   = "AllowApplicationAlerts"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.discord_alerts.function_name
  principal      = "sns.amazonaws.com"
  source_arn     = local.alarm_topic_arn
  source_account = data.aws_caller_identity.observability.account_id
}

resource "aws_sns_topic_subscription" "discord_alerts" {
  depends_on = [
    aws_lambda_permission.discord_alerts, aws_lambda_function_event_invoke_config.discord_alerts,
    aws_sqs_queue_policy.notification_failures
  ]
  topic_arn = local.alarm_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.discord_alerts.arn
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notification_failures.arn
  })
}

# No actions: publishing a relay failure to that same relay would loop.
resource "aws_cloudwatch_metric_alarm" "notification_failures" {
  alarm_name          = "${local.prefix}-notification-failures"
  alarm_description   = "Discord delivery failed; inspect the retained queue and relay metrics. This alarm has no outbound action."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.notification_failures.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = []
  ok_actions          = []
  tags                = var.tags
}
