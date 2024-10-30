# main.tf - General configuration for AWS Provider

provider "aws" {
  region  = "us-east-1"
  profile = "rbouyekhf"
}

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

variable "vpc_value" {
  description = "The vpc id where to deploy the db & lambda."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for RDS and Lambda"
  type        = list(string)
}