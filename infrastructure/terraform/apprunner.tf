# ──────────────────────────────────────────────────────────────────────────────
# AWS App Runner — Managed Serverless Containers
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_apprunner_service" "backend" {
  service_name = "${var.app_name}-backend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }
    image_repository {
      image_identifier      = var.backend_image
      image_repository_type = "ECR"
      image_configuration {
        port = var.backend_port
        runtime_environment_variables = {
          "ENVIRONMENT" = var.environment
          "PORT"        = tostring(var.backend_port)
        }
      }
    }
    auto_deployments_enabled = true # Automatically redeploys when new image pushed to ECR
  }

  instance_configuration {
    cpu    = "1024" # Minimum 1 vCPU
    memory = "2048" # Minimum 2 GB for 1 vCPU
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/"
    healthy_threshold   = 1
    unhealthy_threshold = 5
    interval            = 10
    timeout             = 5
  }

  tags = {
    Name        = "${var.app_name}-backend"
    Environment = var.environment
  }
}
