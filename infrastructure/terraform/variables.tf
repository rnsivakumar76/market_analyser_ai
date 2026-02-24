variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "ap-southeast-1"
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "market-analyser"
}

variable "backend_image" {
  description = "Full ECR image URI for the backend (with tag)"
  type        = string
}

variable "backend_cpu" {
  description = "Fargate CPU units for backend (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "backend_memory" {
  description = "Fargate memory (MB) for backend"
  type        = number
  default     = 512
}

variable "backend_desired_count" {
  description = "Number of Fargate tasks to run"
  type        = number
  default     = 1
}

variable "backend_port" {
  description = "Port the backend FastAPI app listens on"
  type        = number
  default     = 8000
}

variable "availability_zones" {
  description = "List of AZs to use (use 1 to minimize costs)"
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# ──────────────────────────────────────────────────────────────────────────────
# Google Auth & Security
# ──────────────────────────────────────────────────────────────────────────────

variable "google_client_id" {
  description = "Google OAuth Client ID"
  type        = string
  default     = ""
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jwt_secret_key" {
  description = "Secret key for JWT generation (keep this safe!)"
  type        = string
  sensitive   = true
  default     = ""
}
