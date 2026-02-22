# ──────────────────────────────────────────────────────────────────────────────
# IAM — ECS Task Execution Role & Task Role
# ──────────────────────────────────────────────────────────────────────────────

# App Runner Access Role (used to pull images from ECR)
resource "aws_iam_role" "apprunner_access" {
  name = "${var.app_name}-apprunner-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.app_name}-apprunner-access" }
}

resource "aws_iam_role_policy_attachment" "apprunner_access_policy" {
  role       = aws_iam_role.apprunner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# App Runner Instance Role (what the running container is allowed to do)
resource "aws_iam_role" "apprunner_instance" {
  name = "${var.app_name}-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "tasks.apprunner.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.app_name}-apprunner-instance" }
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
        # App Runner permissions — update service & monitor deployment
        Effect = "Allow"
        Action = [
          "apprunner:UpdateService",
          "apprunner:ListServices",
          "apprunner:DescribeCustomDomains",
          "apprunner:DescribeService",
          "apprunner:StartDeployment",
          "apprunner:ListOperations",
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
        # IAM PassRole — needed to pass roles to App Runner
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [
          aws_iam_role.apprunner_access.arn,
          aws_iam_role.apprunner_instance.arn
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
