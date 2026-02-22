terraform {
  backend "s3" {
    bucket  = "heat-chronicle-prod-terraform"
    key     = "aws/terraform.tfstate"
    region  = "ap-northeast-1"
    encrypt = true
  }
}
