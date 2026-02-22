# ──────────────────────────────────────────────────────────────────────────────
# IAM — ECS Task Execution Role & Task Role
# ──────────────────────────────────────────────────────────────────────────────

# Task Execution Role (used by ECS agent to pull images, write logs)
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.app_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.app_name}-ecs-execution-role" }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow ECS to pull from ECR (already included in AmazonECSTaskExecutionRolePolicy)
# Add CloudWatch Logs permission
resource "aws_iam_role_policy" "ecs_task_execution_extras" {
  name = "${var.app_name}-ecs-extras"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Task Role (what the running container is allowed to do)
resource "aws_iam_role" "ecs_task" {
  name = "${var.app_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.app_name}-ecs-task-role" }
}

# GitLab CI/CD deployer user (create manually or via Terraform)
# This policy allows GitLab to push images & update ECS
resource "aws_iam_user" "gitlab_deployer" {
  name = "${var.app_name}-gitlab-deployer"
  tags = { Purpose = "GitLab CI/CD Deployment" }
}

resource "aws_iam_user_policy" "gitlab_deployer" {
  name = "${var.app_name}-gitlab-deployer-policy"
  user = aws_iam_user.gitlab_deployer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # ECR permissions
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ]
        Resource = "*"
      },
      {
        # ECS permissions — update service & monitor deployment
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:ListTaskDefinitions",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
        ]
        Resource = "*"
      },
      {
        # S3 permissions — frontend deployment
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:PutObjectAcl",
        ]
        Resource = [
          aws_s3_bucket.frontend.arn,
          "${aws_s3_bucket.frontend.arn}/*"
        ]
      },
      {
        # CloudFront — invalidate cache after frontend deploy
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
        ]
        Resource = "*"
      },
      {
        # IAM PassRole — needed to register task definitions
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      },
      {
        # Terraform state (S3 + DynamoDB)
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "*"
      }
    ]
  })
}

# Access key for GitLab CI/CD variables
resource "aws_iam_access_key" "gitlab_deployer" {
  user = aws_iam_user.gitlab_deployer.name
}
