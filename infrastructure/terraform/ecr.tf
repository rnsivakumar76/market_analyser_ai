# ──────────────────────────────────────────────────────────────────────────────
# ECR Repositories — SHARED across all environments
# These are created once and referenced by all workspaces.
# Different environments use different image tags (:latest for prod, :dev for dev)
# ──────────────────────────────────────────────────────────────────────────────

locals {
  is_primary = var.environment == "production"
}

# Use data sources to reference existing ECR repos (created by prod workspace)
data "aws_ecr_repository" "backend" {
  count = local.is_primary ? 0 : 1
  name  = "${var.app_name}-backend"
}

data "aws_ecr_repository" "frontend" {
  count = local.is_primary ? 0 : 1
  name  = "${var.app_name}-frontend"
}

# Only create ECR repos in the primary (production) workspace
resource "aws_ecr_repository" "backend" {
  count                = local.is_primary ? 1 : 0
  name                 = "${var.app_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.app_name}-backend"
    Environment = "shared"
  }
}

resource "aws_ecr_repository" "frontend" {
  count                = local.is_primary ? 1 : 0
  name                 = "${var.app_name}-frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.app_name}-frontend"
    Environment = "shared"
  }
}

# Lifecycle policy: keep only the last 5 images to minimize ECR storage costs
resource "aws_ecr_lifecycle_policy" "backend" {
  count      = local.is_primary ? 1 : 0
  repository = aws_ecr_repository.backend[0].name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  count      = local.is_primary ? 1 : 0
  repository = aws_ecr_repository.frontend[0].name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# Local values to get repo URLs regardless of workspace
locals {
  ecr_backend_url  = local.is_primary ? aws_ecr_repository.backend[0].repository_url : data.aws_ecr_repository.backend[0].repository_url
  ecr_frontend_url = local.is_primary ? aws_ecr_repository.frontend[0].repository_url : data.aws_ecr_repository.frontend[0].repository_url
}
