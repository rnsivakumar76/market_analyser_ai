# ──────────────────────────────────────────────────────────────────────────────
# Import existing dev resources into fresh Terraform state
# ──────────────────────────────────────────────────────────────────────────────

# S3 Buckets
import {
  to = aws_s3_bucket.frontend
  id = "market-analyser-frontend-dev-614686365382"
}

import {
  to = aws_s3_bucket.config
  id = "market-analyser-config-dev-614686365382"
}

import {
  to = aws_s3_bucket_website_configuration.frontend
  id = "market-analyser-frontend-dev-614686365382"
}

import {
  to = aws_s3_bucket_public_access_block.frontend
  id = "market-analyser-frontend-dev-614686365382"
}

import {
  to = aws_s3_bucket_public_access_block.config
  id = "market-analyser-config-dev-614686365382"
}

import {
  to = aws_s3_bucket_policy.frontend_public
  id = "market-analyser-frontend-dev-614686365382"
}

# Lambda
import {
  to = aws_lambda_function.api
  id = "market-analyser-api-dev"
}

# API Gateway
import {
  to = aws_apigatewayv2_api.http_api
  id = "u50e9kfngd"
}

import {
  to = aws_apigatewayv2_stage.default
  id = "u50e9kfngd/$default"
}

import {
  to = aws_apigatewayv2_integration.lambda
  id = "u50e9kfngd/pf2wgy9"
}

import {
  to = aws_apigatewayv2_route.proxy
  id = "u50e9kfngd/4fqqxah"
}

# IAM Role
import {
  to = aws_iam_role.lambda_exec
  id = "market-analyser-lambda-exec-dev"
}

import {
  to = aws_iam_role_policy.lambda_s3_config
  id = "market-analyser-lambda-exec-dev:market-analyser-lambda-s3-config-dev"
}

import {
  to = aws_iam_role_policy.lambda_dynamodb
  id = "market-analyser-lambda-exec-dev:market-analyser-lambda-dynamodb-dev"
}

# DynamoDB
import {
  to = aws_dynamodb_table.nexus
  id = "nexus-dev"
}
