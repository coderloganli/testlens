terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.67"
    }
  }

  # Configure remote state before the first apply, for example:
  # backend "s3" {
  #   bucket       = "<state-bucket>"
  #   key          = "testlens/dev/terraform.tfstate"
  #   region       = "us-east-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "testlens"
      Environment = "dev"
    }
  }
}
