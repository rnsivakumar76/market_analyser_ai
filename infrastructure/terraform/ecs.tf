# ──────────────────────────────────────────────────────────────────────────────
# CloudWatch Log Groups
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.app_name}-backend"
  retention_in_days = 7   # Keep logs 7 days to minimize cost

  tags = { Name = "${var.app_name}-backend-logs" }
}

# ──────────────────────────────────────────────────────────────────────────────
# ECS Cluster
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"   # Disable to avoid extra CloudWatch costs
  }

  tags = {
    Name        = "${var.app_name}-cluster"
    Environment = var.environment
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE_SPOT"   # Cheaper — up to 70% off Fargate price
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# ECS Task Definition
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.app_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu    # 256 = 0.25 vCPU
  memory                   = var.backend_memory # 512 MB
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = var.backend_image
      essential = true

      portMappings = [{
        containerPort = var.backend_port
        protocol      = "tcp"
      }]

      environment = [
        { name = "PORT", value = tostring(var.backend_port) },
        { name = "ENVIRONMENT", value = var.environment },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.backend_port}/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.app_name}-backend"
    Environment = var.environment
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# ECS Service (Fargate)
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_ecs_service" "backend" {
  name            = "${var.app_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count

  # Use FARGATE_SPOT for cost savings (falls back to FARGATE if spot unavailable)
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 2
    base              = 0
  }
  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true   # No NAT gateway needed
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.backend_port
  }

  # Rolling update — zero downtime deployments
  deployment_controller {
    type = "ECS"
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  # Ignore image changes — CI/CD handles force-new-deployment
  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name        = "${var.app_name}-backend-service"
    Environment = var.environment
  }
}
