resource "aws_ecr_repository" "meet_assist_repo" {
  name = "meet-assist-repo"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.meet_assist_repo.repository_url
}

# Use provisioners to initialize the database tables after creation
resource "null_resource" "upload_docker_img" {
  depends_on = [aws_ecr_repository.meet_assist_repo]
  
  triggers = {
    script_hash1 = file("scripts/upload_docker_img.sh"),
    script_hash2 = file("utils/helpers.py"),
    script_hash3 = file("utils/constants.py"),
    script_hash4 = file("utils/meetings_api_lambda.py"),
    script_hash5 = file("resources/conformity_prompt.txt"),
    script_hash6 = file("resources/initial_prompt.txt"),
    script_hash7 = file("resources/tools_functions.json"),
    script_hash7 = file("resources/app_presentation.txt")
  }

  provisioner "local-exec" {
    command = "bash ./scripts/upload_docker_img.sh ${var.region} ${aws_ecr_repository.meet_assist_repo.repository_url}"
  }
}

data "aws_ecr_image" "latest_meet_assist_image" {
  depends_on       = [null_resource.upload_docker_img]
  repository_name = aws_ecr_repository.meet_assist_repo.name
  most_recent     = true
}

resource "aws_security_group" "fargate_sg" {
  name        = "fargate-meeet-assist-sg"
  description = "Allow HTTP access to Fargate"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8501
    to_port     = 8501
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

# ECS Cluster
resource "aws_ecs_cluster" "meet_assist_cluster" {
  name = "meet-assist-cluster"
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach additional policy to allow Lambda invocation and OpenAI API access if needed
resource "aws_iam_role_policy" "ecs_custom_policy" {
  name = "ecs-custom-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "lambda:InvokeFunction"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "meet_assist_task" {
  family                   = "meet-assist-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn
  container_definitions = jsonencode([
    {
      name      = "meet-assist-container",
      image     = "${aws_ecr_repository.meet_assist_repo.repository_url}@${data.aws_ecr_image.latest_meet_assist_image.image_digest}",  # Replace with your image URL
      portMappings = [
        {
          containerPort = 8501
          hostPort      = 8501
        }
      ],
      environment = [
        {
          name  = "FUNCTION_NAME"
          value = aws_lambda_function.my_lambda.arn
        },
        {
            name = "OPENAI_API_KEY"
            value = local.openai_key
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/meet_assist"
          "awslogs-region"        = var.region  
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# ECS Service to Run the Task Definition
resource "aws_ecs_service" "meet_assist_service" {
  name            = "meet-assist-service"
  cluster         = aws_ecs_cluster.meet_assist_cluster.id
  task_definition = aws_ecs_task_definition.meet_assist_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  force_new_deployment = true  # Force ECS to pull the latest image
  
  network_configuration {
    subnets         = data.aws_subnets.default_vpc_subnets.ids
    security_groups = [aws_security_group.fargate_sg.id]
    assign_public_ip = true  # Set to true if your Fargate task needs a public IP
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app_tg.arn
    container_name   = "meet-assist-container"
    container_port   = 8501
  }
  depends_on = [aws_cloudwatch_log_group.meet_assist_logs, aws_lb_listener.app_listener]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "meet_assist_logs" {
  name              = "/ecs/meet_assist"
  retention_in_days = 1
}