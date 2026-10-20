# The AWS prod root imports the existing repository policy before managing it.
# Keep the ARN independent of the Lambda resource so the policy can precede it.
resource "aws_ecr_repository_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "LambdaECRImageRetrievalPolicy"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = "arn:${data.aws_partition.observability.partition}:lambda:${var.aws_region}:${data.aws_caller_identity.observability.account_id}:function:${local.function_name}"
        }
      }
    }]
  })
}
