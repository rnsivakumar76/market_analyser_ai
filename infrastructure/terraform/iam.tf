# ──────────────────────────────────────────────────────────────────────────────
# IAM — Lambda & GitLab Deployment Roles
# ──────────────────────────────────────────────────────────────────────────────

# Lambda Execution Role (used by AWS Lambda to run the function and write logs to CloudWatch)
resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.app_name}-lambda-exec" }
}

resource "aws_iam_role_policy_attachment" "lambda_exec_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_config" {
  name = "${var.app_name}-lambda-s3-config-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.app_name}-lambda-dynamodb-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.nexus.arn,
          "${aws_dynamodb_table.nexus.arn}/index/*"
        ]
      }
    ]
  })
}

# GitLab CI/CD deployer user
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
        Effect = "Allow"
        Action = ["ecr:*", "lambda:*", "apigateway:*", "s3:*", "cloudfront:*", "iam:PassRole", "events:*"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_access_key" "gitlab_deployer" {
  user = aws_iam_user.gitlab_deployer.name
}
