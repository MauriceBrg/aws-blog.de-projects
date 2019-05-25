provider "aws" {
  region = "${var.region}"
  profile = "${var.profile}"
}

variable "region" {
  default     = "eu-central-1"
  description = "The region the resources will be created in."
}

variable "stage" {
  default = "dev"
}

variable "profile" {
  type = "string"
}

resource "aws_s3_bucket" "demo_bucket" {

  bucket_prefix = "bucket-in-${var.region}-stage-${var.stage}"

  versioning {
    enabled = true
  }
}

terraform {
  required_version = "~> 0.11"

  backend "s3" {
    encrypt = true
  }
}