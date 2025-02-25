terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.88"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  namespace = join("-", split(" ", lower(var.name)))
  path      = format("/%s/", join("/", split(" ", lower(var.name))))
}
