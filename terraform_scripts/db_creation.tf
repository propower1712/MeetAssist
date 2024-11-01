# First Script: Create an RDS Database with a Table

# db_creation.tf - Create MySQL RDS Database

resource "aws_security_group" "rds_sg" {
  name        = "rds_security_group"
  description = "Allow MySQL access"
  vpc_id      = data.aws_vpc.default.id

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
  db_name              = var.db_name
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
    script_hash = filebase64sha256("../scripts/initialize_db.sh")
  }

  provisioner "local-exec" {
    command = "bash ../scripts/initialize_db.sh ${aws_db_instance.assistant_dev.address} ${var.rds_username} ${var.rds_password} ${var.db_name}"
  }
}

# Outputs
output "rds_endpoint" {
  value = aws_db_instance.assistant_dev.address
  description = "The endpoint of the RDS instance."
}

# To Destroy Resources
# Run terraform destroy to remove all infrastructure
