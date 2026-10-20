output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.backend.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.backend.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.backend.arn
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "api_domain_url" {
  description = "API custom domain URL"
  value       = "https://${var.api_domain_name}"
}

output "api_observability" {
  description = "Application-owned log group, alarm names and notification topic"
  value = {
    access_log_group               = aws_cloudwatch_log_group.api_access.name
    topic_arn                      = local.alarm_topic_arn
    discord_webhook_parameter_name = aws_ssm_parameter.discord_webhook.name
    discord_function_name          = aws_lambda_function.discord_alerts.function_name
    notification_failure_queue_url = aws_sqs_queue.notification_failures.url
    notification_failure_alarm     = aws_cloudwatch_metric_alarm.notification_failures.alarm_name
    alarm_names = concat(
      [for alarm in aws_cloudwatch_metric_alarm.api : alarm.alarm_name],
      [for alarm in aws_cloudwatch_metric_alarm.lambda : alarm.alarm_name],
      [aws_cloudwatch_metric_alarm.api_throttles.alarm_name]
    )
  }
}
