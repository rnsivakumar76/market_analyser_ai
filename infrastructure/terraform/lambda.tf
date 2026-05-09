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
      SESSION_SECRET       = var.session_secret
      TWELVEDATA_API_KEY   = var.twelvedata_api_key
      FMP_API_KEY          = var.fmp_api_key
      NEWS_API_KEY         = var.news_api_key
      TELEGRAM_BOT_TOKEN   = var.telegram_bot_token
      TELEGRAM_CHAT_ID     = var.telegram_chat_id
      FRONTEND_URL          = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.frontend_fixed.domain_name}"
      GOOGLE_REDIRECT_URI   = var.domain_name != "" ? "https://${var.domain_name}/api/auth/callback" : "https://${aws_cloudfront_distribution.frontend_fixed.domain_name}/api/auth/callback"
      LOG_LEVEL             = "INFO"
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
  name                = "${var.app_name}-5min-analysis${local.env_suffix}"
  description         = "Trigger market analysis every 5 minutes"
  schedule_expression = "rate(5 minutes)"
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
      "host": "localhost",
      "x-internal-trigger": "scheduler"
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

# ──────────────────────────────────────────────────────────────────────────────
# Intraday Signal Scanner — runs every 15 minutes via EventBridge
# Calls POST /api/signals/scan to detect EMA/MACD crossovers on 15m/1H/4H
# ──────────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_event_rule" "signal_scan" {
  name                = "${var.app_name}-signal-scan${local.env_suffix}"
  description         = "Run intraday signal scan every 15 minutes"
  schedule_expression = "rate(15 minutes)"
}

resource "aws_cloudwatch_event_target" "signal_scan_target" {
  rule      = aws_cloudwatch_event_rule.signal_scan.name
  target_id = "TriggerSignalScan"
  arn       = aws_lambda_function.api.arn

  input = jsonencode({
    "version"        : "2.0",
    "routeKey"       : "POST /api/signals/scan",
    "rawPath"        : "/api/signals/scan",
    "rawQueryString" : "",
    "headers"        : {
      "host"                : "localhost",
      "x-internal-trigger"  : "signal-scanner",
      "content-type"        : "application/json"
    },
    "requestContext" : {
      "http" : {
        "method"   : "POST",
        "path"     : "/api/signals/scan",
        "sourceIp" : "127.0.0.1"
      }
    },
    "body"           : "{}",
    "isBase64Encoded": false
  })
}

resource "aws_lambda_permission" "eventbridge_signal_scan" {
  statement_id  = "AllowSignalScanFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.signal_scan.arn
}
