# First Script: Create an RDS Database with a Table

# main.tf - Create MySQL RDS Database
provider "aws" {
  region = "us-east-1"
  profile = "rbouyekhf"
}

variable "rds_username" {
  description = "The username for the RDS instance."
  type        = string
}

variable "rds_password" {
  description = "The password for the RDS instance."
  type        = string
  sensitive   = true
}

resource "aws_security_group" "rds_sg" {
  name        = "rds_security_group"
  description = "Allow MySQL access"
  vpc_id      = "vpc-0580e21abcd7c38a8"

  ingress {
    description = "Allow MySQL access from my IP"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "assistant_dev" {
  allocated_storage    = 10
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t4g.micro"  # Lightest instance for learning purposes
  db_name                 = "assistant"
  username             = var.rds_username
  password             = var.rds_password
  publicly_accessible = true
  skip_final_snapshot  = true
  backup_retention_period = 0
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  # Tags for better identification
  tags = {
    Name = "meet-assist"
  }
}

# Use provisioners to initialize the database tables after creation
resource "null_resource" "initialize_db" {
  depends_on = [aws_db_instance.assistant_dev]

  triggers = {
    always_run = "${timestamp()}"
  }
  provisioner "local-exec" {
    command = "bash ./scripts/initialize_db.sh ${aws_db_instance.assistant_dev.address} ${var.rds_username} ${var.rds_password}"
  }
}

# Outputs
output "rds_endpoint" {
  value = aws_db_instance.assistant_dev.address
  description = "The endpoint of the RDS instance."
}

# To Destroy Resources
# Run terraform destroy to remove all infrastructure
