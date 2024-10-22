# First Script: Create an RDS Database with a Table

# main.tf - Create MySQL RDS Database
provider "aws" {
  region = "us-east-1"
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

resource "aws_db_instance" "assistant_dev" {
  allocated_storage    = 20
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t4g.micro"  # Lightest instance for learning purposes
  name                 = "assistant"
  username             = var.rds_username
  password             = var.rds_password
  publicly_accessible = false
  skip_final_snapshot  = true
  backup_retention_period = 0

  # Tags for better identification
  tags = {
    Name = "meet-assist"
  }
}

# Use provisioners to initialize the database tables after creation
resource "null_resource" "initialize_db" {
  depends_on = [aws_db_instance.assistant_dev]

  provisioner "local-exec" {
    command = <<EOT
      mysql -h ${aws_db_instance.assistant_dev.address} -P 3306 -u ${var.rds_username} -p${var.rds_password} -e "CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL
      );"

      mysql -h ${aws_db_instance.assistant_dev.address} -P 3306 -u ${var.rds_username} -p${var.rds_password} -e "CREATE TABLE IF NOT EXISTS meetings (
        meeting_id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        description TEXT
      );"

      mysql -h ${aws_db_instance.assistant_dev.address} -P 3306 -u ${var.rds_username} -p${var.rds_password} -e "CREATE TABLE IF NOT EXISTS meeting_participants (
        meeting_id INT,
        email VARCHAR(255),
        PRIMARY KEY (meeting_id, email),
        FOREIGN KEY (meeting_id) REFERENCES meetings (meeting_id),
        FOREIGN KEY (email) REFERENCES users (email)
      );"

      mysql -h ${aws_db_instance.assistant_dev.address} -P 3306 -u ${var.rds_username} -p${var.rds_password} assistant -e "LOAD DATA LOCAL INFILE 'input/users.csv' INTO TABLE users FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES (name, email);"

      mysql -h ${aws_db_instance.assistant_dev.address} -P 3306 -u ${var.rds_username} -p${var.rds_password} assistant -e "LOAD DATA LOCAL INFILE 'input/meetings.csv' INTO TABLE meetings FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES (title, start_time, end_time, description);"

      mysql -h ${aws_db_instance.assistant_dev.address} -P 3306 -u ${var.rds_username} -p${var.rds_password} assistant -e "LOAD DATA LOCAL INFILE 'input/meeting_participants_v2.csv' INTO TABLE meeting_participants FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES (meeting_id, email);"
    EOT
  }
}

# Outputs
output "rds_endpoint" {
  value = aws_db_instance.assistant_dev.address
  description = "The endpoint of the RDS instance."
}

# To Destroy Resources
# Run terraform destroy to remove all infrastructure
