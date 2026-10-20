terraform {
  required_version = ">= 1.16.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.54"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "test_id" {
  type = string
  validation {
    condition     = can(regex("^issue5-[a-z0-9-]{1,20}$", var.test_id))
    error_message = "Use an isolated issue5- prefixed test name."
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      System      = "heat-chronicle"
      Environment = "capacity-test"
      ManagedBy   = "Terraform"
      Issue       = "5"
    }
  }
}

locals {
  prefix = "heat-capacity-${var.test_id}"
}

resource "aws_iam_role" "fixture" {
  name = local.prefix
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "fixture" {
  name              = "/aws/lambda/${local.prefix}"
  retention_in_days = 1
}

resource "aws_iam_role_policy" "logs" {
  role = aws_iam_role.fixture.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.fixture.arn}:*"
    }]
  })
}

resource "aws_lambda_function" "fixture" {
  function_name                  = local.prefix
  role                           = aws_iam_role.fixture.arn
  runtime                        = "python3.14"
  handler                        = "fixture.handler"
  filename                       = "${path.module}/fixture.zip"
  source_code_hash               = filebase64sha256("${path.module}/fixture.zip")
  memory_size                    = 128
  timeout                        = 10
  reserved_concurrent_executions = 5
  depends_on                     = [aws_iam_role_policy.logs]
}

resource "aws_apigatewayv2_api" "fixture" {
  name          = local.prefix
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins  = ["http://localhost:4173"]
    allow_methods  = ["GET"]
    allow_headers  = ["Content-Type"]
    expose_headers = ["Retry-After"]
  }
}

resource "aws_apigatewayv2_integration" "fixture" {
  api_id                 = aws_apigatewayv2_api.fixture.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fixture.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.fixture.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.fixture.id}"
}

resource "aws_apigatewayv2_route" "fetch_month" {
  api_id    = aws_apigatewayv2_api.fixture.id
  route_key = "GET /api/temperature/{station_id}/fetch-month"
  target    = "integrations/${aws_apigatewayv2_integration.fixture.id}"
}

resource "aws_apigatewayv2_stage" "fixture" {
  api_id      = aws_apigatewayv2_api.fixture.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_rate_limit  = 5
    throttling_burst_limit = 10
  }
  route_settings {
    route_key              = aws_apigatewayv2_route.fetch_month.route_key
    throttling_rate_limit  = 1
    throttling_burst_limit = 2
  }
}

resource "aws_lambda_permission" "gateway" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fixture.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.fixture.execution_arn}/*/*"
}

output "capacity_test" {
  value = {
    environment   = "capacity-test"
    endpoint      = aws_apigatewayv2_api.fixture.api_endpoint
    function_name = aws_lambda_function.fixture.function_name
    api_id        = aws_apigatewayv2_api.fixture.id
    region        = var.aws_region
  }
}
