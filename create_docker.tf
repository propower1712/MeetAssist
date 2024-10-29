# # Provider
# provider "aws" {
#   region = "us-east-1"  # Replace with your preferred region
# }

# # Define your VPC, Subnets, and Security Group (if not already created)
# data "aws_vpc" "default" {
#   default = true
# }

# data "aws_subnet_ids" "default" {
#   vpc_id = data.aws_vpc.default.id
# }

# resource "aws_security_group" "fargate_sg" {
#   name        = "fargate-streamlit-sg"
#   description = "Allow HTTP access to Fargate"
#   vpc_id      = data.aws_vpc.default.id

#   ingress {
#     from_port   = 80
#     to_port     = 80
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

# # Define an ECS Cluster
# resource "aws_ecs_cluster" "streamlit_cluster" {
#   name = "streamlit-cluster"
# }

# # IAM Role for ECS Task Execution
# resource "aws_iam_role" "ecs_task_execution_role" {
#   name = "ecs-task-execution-role"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Action = "sts:AssumeRole",
#         Effect = "Allow",
#         Principal = {
#           Service = "ecs-tasks.amazonaws.com"
#         }
#       }
#     ]
#   })
# }

# # Attach AWS managed policy for ECS task execution
# resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
#   role       = aws_iam_role.ecs_task_execution_role.name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
# }

# # ECS Task Definition
# resource "aws_ecs_task_definition" "streamlit_task" {
#   family                   = "streamlit-task"
#   network_mode             = "awsvpc"
#   requires_compatibilities = ["FARGATE"]
#   cpu                      = "256"   # Adjust CPU for your needs
#   memory                   = "512"   # Adjust memory for your needs
#   execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

#   container_definitions = jsonencode([
#     {
#       name      = "streamlit-container",
#       image     = "your_docker_image_url",  # Replace with your image URL
#       portMappings = [
#         {
#           containerPort = 80
#           hostPort      = 80
#         }
#       ],
#       environment = [
#         {
#           name  = "AWS_REGION"
#           value = "us-east-1"  # Replace with your region
#         },
#         {
#           name  = "LAMBDA_FUNCTION_NAME"
#           value = "your_lambda_function_name"  # Replace with your Lambda function name
#         }
#       ],
#       logConfiguration = {
#         logDriver = "awslogs"
#         options = {
#           "awslogs-group"         = "/ecs/streamlit"
#           "awslogs-region"        = "us-east-1"  # Replace with your region
#           "awslogs-stream-prefix" = "ecs"
#         }
#       }
#     }
#   ])
# }

# # ECS Service to Run the Task Definition
# resource "aws_ecs_service" "streamlit_service" {
#   name            = "streamlit-service"
#   cluster         = aws_ecs_cluster.streamlit_cluster.id
#   task_definition = aws_ecs_task_definition.streamlit_task.arn
#   desired_count   = 1
#   launch_type     = "FARGATE"
#   network_configuration {
#     subnets         = data.aws_subnet_ids.default.ids
#     security_groups = [aws_security_group.fargate_sg.id]
#     assign_public_ip = true  # Set to true if your Fargate task needs a public IP
#   }
#   depends_on = [aws_cloudwatch_log_group.streamlit_logs]
# }

# # CloudWatch Log Group for Streamlit Logs
# resource "aws_cloudwatch_log_group" "streamlit_logs" {
#   name              = "/ecs/streamlit"
#   retention_in_days = 7
# }
