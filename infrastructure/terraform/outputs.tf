output "apprunner_url" {
  description = "App Runner Service URL — use this for direct backend access or health checks"
  value       = aws_apprunner_service.backend.service_url
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

output "apprunner_service_arn" {
  description = "App Runner service ARN"
  value       = aws_apprunner_service.backend.arn
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
    apprunner    = "~$5-10/mo (1 vCPU, 2GB memory, scaled to minimum 1 instance)"
    cloudfront   = "~$0 (free tier 1TB/mo)"
    s3           = "~$0 (free tier 5GB)"
    ecr          = "~$0 (free tier 500MB)"
    total        = "~$5-10/mo running 24/7 with zero traffic. Much cheaper than ALB!"
  }
}
