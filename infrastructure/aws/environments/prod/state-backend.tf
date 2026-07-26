resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = "heat-chronicle-prod-terraform"

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = "heat-chronicle-prod-terraform"

  rule {
    id     = "expire-noncurrent-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

data "aws_iam_policy_document" "terraform_state" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      "arn:aws:s3:::heat-chronicle-prod-terraform",
      "arn:aws:s3:::heat-chronicle-prod-terraform/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "terraform_state" {
  bucket = "heat-chronicle-prod-terraform"
  policy = data.aws_iam_policy_document.terraform_state.json
}
