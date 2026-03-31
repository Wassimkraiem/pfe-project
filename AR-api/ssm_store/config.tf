terraform {
  backend "s3" {
    bucket  = "bviral-tfstate"
    encrypt = true
    key     = "ssm_authentic_rights_api.tfstate"
    region  = "us-east-1"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.55.0"
    }
  }
}
