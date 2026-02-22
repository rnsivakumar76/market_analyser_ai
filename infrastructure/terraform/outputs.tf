output "api_gateway_url" {
  description = "API Gateway URL — use this for direct backend access or health checks"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "frontend_url" {
  description = "S3 Website URL — direct access to frontend"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "cloudfront_url" {
  description = "CloudFront URL — this is your public app URL"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — used by CI/CD to invalidate cache"
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_s3_bucket" {
  description = "S3 bucket name for the frontend — CI/CD syncs build artifacts here"
  value       = aws_s3_bucket.frontend.bucket
}

output "ecr_backend_url" {
  description = "ECR repository URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for the frontend image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "lambda_function_arn" {
  description = "Backend Lambda function ARN"
  value       = aws_lambda_function.api.arn
}

output "gitlab_deployer_access_key_id" {
  description = "AWS Access Key ID for GitLab CI/CD — add to GitLab CI/CD Variables"
  value       = aws_iam_access_key.gitlab_deployer.id
  sensitive   = true
}

output "gitlab_deployer_secret_access_key" {
  description = "AWS Secret Key for GitLab CI/CD — add to GitLab CI/CD Variables (masked)"
  value       = aws_iam_access_key.gitlab_deployer.secret
  sensitive   = true
}

output "cost_estimate" {
  description = "Estimated monthly AWS costs"
  value = {
    lambda       = "~$0/mo (Free tier includes 1M requests/mo & 3.2M seconds of compute)"
    api_gateway  = "~$0/mo (Free tier includes 1M API calls/mo)"
    cloudfront   = "~$0 (free tier 1TB/mo)"
    s3           = "~$0 (free tier 5GB)"
    ecr          = "~$0 (free tier 500MB)"
    total        = "~$0/mo (100% Free Tier Serverless Architecture!)"
  }
}
