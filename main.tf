terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "tutaia-terraform-state-file"
    key            = "tutaia/platform/terraform.tfstate"
    region         = "eu-central-1"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "tutaia"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ACM certificate must be in us-east-1 for CloudFront
# but since we're using ALB, we use eu-central-1 directly
provider "aws" {
  alias  = "acm"
  region = "eu-central-1"
}

# CloudFront requires ACM certificates in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "tutaia"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
