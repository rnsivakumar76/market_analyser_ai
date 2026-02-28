output "api_gateway_url" {
  description = "API Gateway URL — use this for direct backend access or health checks"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "frontend_url" {
  description = "S3 Website URL — direct access to frontend"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "frontend_s3_bucket" {
  description = "S3 bucket name for the frontend — CI/CD syncs build artifacts here"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_url" {
  description = "CloudFront Distribution URL"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront Distribution ID for cache invalidation"
  value       = aws_cloudfront_distribution.frontend.id
}

output "ecr_backend_url" {
  description = "ECR repository URL for the backend image"
  value       = local.ecr_backend_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for the frontend image"
  value       = local.ecr_frontend_url
}

output "lambda_function_arn" {
  description = "Backend Lambda function ARN"
  value       = aws_lambda_function.api.arn
}

output "lambda_function_name" {
  description = "Backend Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for this environment"
  value       = aws_dynamodb_table.nexus.name
}

output "gitlab_deployer_access_key_id" {
  description = "AWS Access Key ID for GitLab CI/CD — add to GitLab CI/CD Variables"
  value       = local.is_primary ? aws_iam_access_key.gitlab_deployer[0].id : "n/a (dev environment)"
  sensitive   = true
}

output "gitlab_deployer_secret_access_key" {
  description = "AWS Secret Key for GitLab CI/CD — add to GitLab CI/CD Variables (masked)"
  value       = local.is_primary ? aws_iam_access_key.gitlab_deployer[0].secret : "n/a (dev environment)"
  sensitive   = true
}

output "environment" {
  description = "Current deployment environment"
  value       = var.environment
}

output "cost_estimate" {
  description = "Estimated monthly AWS costs"
  value = {
    lambda       = "~$0/mo (Free tier includes 1M requests/mo & 3.2M seconds of compute)"
    api_gateway  = "~$0/mo (Free tier includes 1M API calls/mo)"
    dynamodb     = "~$0/mo (Free tier 25GB + 25 RCU/WCU always free)"
    s3           = "~$0 (free tier 5GB)"
    ecr          = "~$0 (free tier 500MB)"
    total        = "~$0/mo (100% Free Tier Serverless Architecture!)"
  }
}

output "custom_domain_url" {
  description = "Custom Domain URL (if configured)"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "Not configured"
}
