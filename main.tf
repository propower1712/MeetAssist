# Define variables that may be used across multiple resources
variable "rds_username" {
  description = "The username for the RDS instance."
  type        = string
}

variable "rds_password" {
  description = "The password for the RDS instance."
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "The vpc id where to deploy the db & lambda."
  type        = string
}

variable "region" {
  description = "Define the region where to deploy resources."
  type        = string
}

locals {
  # Get JSON data
  config_data = jsondecode(file("config.json"))
  openai_key  = local.config_data.OPENAI_API_KEY
}

# main.tf - General configuration for AWS Provider
provider "aws" {
  region  = var.region
  profile = "rbouyekhf"
}

# Define VPC
data "aws_vpc" "default" {
  default = true
}

# Get the list of subnet IDs for the default VPC
data "aws_subnets" "default_vpc_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}