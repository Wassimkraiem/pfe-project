provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      terraform   = true
      environment = var.ENV
      app         = "ssm_authentic_rights_api"

    }
  }
}
