locals {
  prefix        = "${var.system_name}-${var.environment}"
  function_name = "${local.prefix}-backend"
}

# -----------------------------------------------------------------------------
# Route 53 — Hosted Zone Data Source
# -----------------------------------------------------------------------------
data "aws_route53_zone" "main" {
  name         = var.hosted_zone_name
  private_zone = false
}

# =============================================================================
# 1) ECR Repository
# =============================================================================
resource "aws_ecr_repository" "backend" {
  name                 = "${local.prefix}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-backend"
  })
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the latest 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# =============================================================================
# 2) DynamoDB Tables
# =============================================================================
resource "aws_dynamodb_table" "stations" {
  name         = "${local.prefix}-stations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "N"
  }

  attribute {
    name = "prec_no"
    type = "N"
  }

  global_secondary_index {
    name            = "prec_no-index"
    projection_type = "ALL"

    key_schema {
      attribute_name = "prec_no"
      key_type       = "HASH"
    }
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-stations"
  })
}

resource "aws_dynamodb_table" "daily_temperature" {
  name         = "${local.prefix}-daily-temperature"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "station_id"
  range_key    = "date"

  attribute {
    name = "station_id"
    type = "N"
  }

  attribute {
    name = "date"
    type = "S"
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-daily-temperature"
  })
}

resource "aws_dynamodb_table" "fetch_log" {
  name         = "${local.prefix}-fetch-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "station_id"
  range_key    = "year_month"

  attribute {
    name = "station_id"
    type = "N"
  }

  attribute {
    name = "year_month"
    type = "S"
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-fetch-log"
  })
}

resource "aws_dynamodb_table" "scrape_jobs" {
  name         = "${local.prefix}-scrape-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-scrape-jobs"
  })
}

# =============================================================================
# 3) Lambda IAM Role
# =============================================================================
resource "aws_iam_role" "lambda_execution" {
  name = "${local.prefix}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.prefix}-lambda-execution"
  })
}

resource "aws_iam_policy" "lambda_logs" {
  name = "${local.prefix}-lambda-logs"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
    }]
  })
  tags = var.tags
}

moved {
  from = aws_iam_role_policy_attachment.lambda_basic_execution
  to   = aws_iam_role_policy_attachment.lambda_logs
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_logs.arn

  # Attach the application-scoped policy before detaching the old AWS policy.
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${local.prefix}-lambda-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "StationRead"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:Scan"]
        Resource = [aws_dynamodb_table.stations.arn]
      },
      {
        Sid      = "StationIndexQuery"
        Effect   = "Allow"
        Action   = ["dynamodb:Query"]
        Resource = [aws_dynamodb_table.stations.arn, "${aws_dynamodb_table.stations.arn}/index/prec_no-index"]
      },
      {
        # handler.py runs versioned station migrations on cold start.
        Sid      = "StationMigrations"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:BatchWriteItem"]
        Resource = [aws_dynamodb_table.stations.arn]
      },
      {
        Sid      = "TemperatureData"
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:BatchWriteItem"]
        Resource = [aws_dynamodb_table.daily_temperature.arn]
      },
      {
        Sid      = "FetchLogAndLease"
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
        Resource = [aws_dynamodb_table.fetch_log.arn]
      }
    ]
  })
}

# =============================================================================
# 4) CloudWatch Log Group
# =============================================================================
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 30

  tags = merge(var.tags, {
    Name = "${local.prefix}-lambda-logs"
  })
}

# =============================================================================
# 5) Lambda Function
# =============================================================================
resource "aws_lambda_function" "backend" {
  function_name = local.function_name
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:latest"
  memory_size   = 512
  timeout       = 900

  reserved_concurrent_executions = var.api_capacity.lambda_reserved_concurrency

  environment {
    variables = {
      DYNAMODB_REGION       = var.aws_region
      CORS_ALLOW_ORIGINS    = "https://${var.domain_name}"
      DYNAMODB_TABLE_PREFIX = local.prefix
    }
  }

  depends_on = [
    aws_ecr_repository_policy.backend,
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy.lambda_dynamodb,
  ]

  lifecycle {
    ignore_changes = [image_uri]
  }

  tags = merge(var.tags, {
    Name = local.function_name
  })
}

# =============================================================================
# 6) API Gateway HTTP API
# =============================================================================
resource "aws_apigatewayv2_api" "backend" {
  name          = "${local.prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins     = ["https://${var.domain_name}"]
    allow_methods     = ["GET"]
    allow_headers     = ["accept", "accept-language", "content-language", "content-type"]
    allow_credentials = false
    expose_headers    = ["Retry-After"]
    max_age           = 86400
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-api"
  })
}

resource "aws_apigatewayv2_integration" "backend" {
  api_id                 = aws_apigatewayv2_api.backend.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.backend.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.backend.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

# The explicit route receives a tighter limit than the stage fallback.
resource "aws_apigatewayv2_route" "fetch_month" {
  api_id    = aws_apigatewayv2_api.backend.id
  route_key = "GET /api/temperature/{station_id}/fetch-month"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.backend.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      request_id             = "$context.requestId"
      request_time_epoch     = "$context.requestTimeEpoch"
      route_key              = "$context.routeKey"
      status                 = "$context.status"
      integration_status     = "$context.integration.status"
      lambda_service_status  = "$context.integration.integrationStatus"
      response_latency_ms    = "$context.responseLatency"
      integration_latency_ms = "$context.integrationLatency"
      response_length        = "$context.responseLength"
    })
  }

  default_route_settings {
    throttling_rate_limit  = var.api_capacity.stage_rate
    throttling_burst_limit = var.api_capacity.stage_burst
  }

  route_settings {
    route_key              = aws_apigatewayv2_route.fetch_month.route_key
    throttling_rate_limit  = var.api_capacity.fetch_month_rate
    throttling_burst_limit = var.api_capacity.fetch_month_burst
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-api-default"
  })
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.backend.execution_arn}/*/*"
}

# =============================================================================
# 7) Custom Domain
# =============================================================================
resource "aws_acm_certificate" "api" {
  domain_name       = var.api_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-api"
  })
}

resource "aws_route53_record" "api_acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id         = data.aws_route53_zone.main.zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 300
  records         = [each.value.record]
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for record in aws_route53_record.api_acm_validation : record.fqdn]
}

resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = var.api_domain_name

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.api.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge(var.tags, {
    Name = "${local.prefix}-api-domain"
  })
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = aws_apigatewayv2_api.backend.id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = aws_apigatewayv2_stage.default.id
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
