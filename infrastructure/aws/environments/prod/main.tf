locals {
  tags = {
    System      = var.system_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------------
# Static Site (S3 + CloudFront)
# -----------------------------------------------------------------------------
module "static_site" {
  source = "../../modules/static_site"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  system_name         = var.system_name
  environment         = var.environment
  default_root_object = "index.html"
  domain_name         = var.domain_name
  hosted_zone_name    = var.hosted_zone_name
  tags                = local.tags
}

# -----------------------------------------------------------------------------
# Backend API (ECR + DynamoDB + Lambda + API Gateway)
# -----------------------------------------------------------------------------
module "backend_api" {
  source = "../../modules/backend_api"

  system_name      = var.system_name
  environment      = var.environment
  aws_region       = var.aws_region
  domain_name      = var.domain_name
  api_domain_name  = var.api_domain_name
  hosted_zone_name = var.hosted_zone_name
  tags             = local.tags
}

# -----------------------------------------------------------------------------
# GitHub Actions OIDC Provider
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = local.tags
}

# -----------------------------------------------------------------------------
# GitHub Actions Deploy Role
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:*"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = "${var.system_name}-${var.environment}-github-actions-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json

  tags = local.tags
}

data "aws_iam_policy_document" "github_actions_deploy" {
  # S3 deploy permissions
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      module.static_site.s3_bucket_arn,
      "${module.static_site.s3_bucket_arn}/*",
    ]
  }

  # CloudFront cache invalidation
  statement {
    effect = "Allow"
    actions = [
      "cloudfront:CreateInvalidation",
    ]
    resources = [
      module.static_site.cloudfront_distribution_arn,
    ]
  }

  # ECR authentication
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  # ECR repository operations
  statement {
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
    ]
    resources = [
      module.backend_api.ecr_repository_arn,
    ]
  }

  # Lambda deploy
  statement {
    effect = "Allow"
    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:GetFunction",
    ]
    resources = [
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.system_name}-${var.environment}-backend",
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "${var.system_name}-${var.environment}-deploy"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}
