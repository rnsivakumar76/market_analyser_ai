# ──────────────────────────────────────────────────────────────────────────────
# AWS Lambda & API Gateway (Zero-cost Serverless Backend)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_lambda_function" "api" {
  function_name = "${var.app_name}-api${local.env_suffix}"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = var.backend_image
  
  # Max 15 minutes timeout to ensure long data fetching (like yfinance) isn't killed
  timeout       = 900 
  memory_size   = 3008

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      CONFIG_S3_BUCKET     = aws_s3_bucket.config.bucket
      DYNAMODB_TABLE       = aws_dynamodb_table.nexus.name
      GOOGLE_CLIENT_ID     = var.google_client_id
      GOOGLE_CLIENT_SECRET = var.google_client_secret
      JWT_SECRET_KEY       = var.jwt_secret_key
      FRONTEND_URL         = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
    }
  }

  tags = {
    Name        = "${var.app_name}-api"
    Environment = var.environment
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# HTTP API Gateway (v2) — Maps endpoints to Lambda
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.app_name}-http-api${local.env_suffix}"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

# Ensure all routes proxy directly to the FastAPI Mangum handler
resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Allow API gateway to invoke Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# ──────────────────────────────────────────────────────────────────────────────
# Scheduled EventBridge to replace apscheduler
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_event_rule" "hourly_analysis" {
  name                = "${var.app_name}-15min-analysis${local.env_suffix}"
  description         = "Trigger market analysis every 15 minutes"
  schedule_expression = "rate(15 minutes)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.hourly_analysis.name
  target_id = "TriggerLambdaAnalysis"
  arn       = aws_lambda_function.api.arn
  
  # Mangum handler expects an API Gateway v2 event payload. We mock an HTTP GET request to /api/analyze here!
  input = jsonencode({
    "version": "2.0",
    "routeKey": "GET /api/analyze",
    "rawPath": "/api/analyze",
    "rawQueryString": "",
    "headers": {
      "host": "localhost"
    },
    "requestContext": {
      "http": {
        "method": "GET",
        "path": "/api/analyze",
        "sourceIp": "127.0.0.1"
      }
    },
    "isBase64Encoded": false
  })
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_analysis.arn
}
