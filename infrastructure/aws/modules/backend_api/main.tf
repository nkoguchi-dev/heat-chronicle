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
    hash_key        = "prec_no"
    projection_type = "ALL"
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

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${local.prefix}-lambda-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
        ]
        Resource = [
          aws_dynamodb_table.stations.arn,
          "${aws_dynamodb_table.stations.arn}/index/*",
          aws_dynamodb_table.daily_temperature.arn,
          "${aws_dynamodb_table.daily_temperature.arn}/index/*",
          aws_dynamodb_table.fetch_log.arn,
          "${aws_dynamodb_table.fetch_log.arn}/index/*",
          aws_dynamodb_table.scrape_jobs.arn,
          "${aws_dynamodb_table.scrape_jobs.arn}/index/*",
        ]
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

  environment {
    variables = {
      DYNAMODB_REGION       = var.aws_region
      CORS_ALLOW_ORIGINS    = "https://${var.domain_name}"
      DYNAMODB_TABLE_PREFIX = local.prefix
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_basic_execution,
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
    allow_origins = ["https://${var.domain_name}"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 86400
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

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.backend.id
  name        = "$default"
  auto_deploy = true

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
