output "alb_dns_name" {
  description = "ALB DNS — use this for direct backend access or health checks"
  value       = aws_lb.backend.dns_name
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

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name for backend"
  value       = aws_ecs_service.backend.name
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
    fargate_spot = "~$3-7/mo (0.25 vCPU, 512MB, 24/7, SPOT pricing)"
    alb          = "~$16/mo (minimum)"
    cloudfront   = "~$0 (free tier 1TB/mo)"
    s3           = "~$0 (free tier 5GB)"
    ecr          = "~$0 (free tier 500MB)"
    total        = "~$20-25/mo running 24/7. Stop ECS task when not in use = ~$1/mo"
  }
}
