terraform {
  backend "s3" {
    bucket  = "heat-chronicle-prod-terraform"
    key     = "github/terraform.tfstate"
    region  = "ap-northeast-1"
    encrypt = true
  }
}
