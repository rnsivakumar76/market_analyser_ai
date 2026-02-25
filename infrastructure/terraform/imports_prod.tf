# ──────────────────────────────────────────────────────────────────────────────
# Import existing production resources to resolve "Resource already exists" errors
# This file RESOLVES the ResourceConflictException during production deployment.
# ──────────────────────────────────────────────────────────────────────────────

# 1. DynamoDB Table
import {
  to = aws_dynamodb_table.nexus
  id = "nexus-production"
}

# 2. IAM Role for Lambda
import {
  to = aws_iam_role.lambda_exec
  id = "market-analyser-lambda-exec-production"
}

# 3. S3 Buckets
import {
  to = aws_s3_bucket.frontend
  id = "market-analyser-frontend-614686365382"
}

import {
  to = aws_s3_bucket.config
  id = "market-analyser-config-614686365382"
}

# 4. ECR Repositories (Shared/Prod)
import {
  to = aws_ecr_repository.frontend[0]
  id = "market-analyser-frontend"
}

import {
  to = aws_ecr_repository.backend[0]
  id = "market-analyser-backend"
}

# 5. GitHub OIDC (Shared/Prod)
import {
  to = aws_iam_openid_connect_provider.github[0]
  id = "arn:aws:iam::614686365382:oidc-provider/token.actions.githubusercontent.com"
}

import {
  to = aws_iam_role.github_actions[0]
  id = "github-actions-market-analyser"
}

import {
  to = aws_iam_role_policy_attachment.github_actions_admin[0]
  id = "github-actions-market-analyser/arn:aws:iam::aws:policy/AdministratorAccess"
}

# 6. Lambda Function (Fixes CreateFunction 409 Conflict)
import {
  to = aws_lambda_function.api
  id = "market-analyser-api"
}

# 7. EventBridge Rule (Fixes CreateRule Conflict)
import {
  to = aws_cloudwatch_event_rule.hourly_analysis
  id = "market-analyser-5min-analysis"
}
