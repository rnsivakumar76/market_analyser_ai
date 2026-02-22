# ──────────────────────────────────────────────────────────────────────────────
# GitHub OIDC Setup
# Allows GitHub Actions to deploy to AWS without storing access keys!
# ──────────────────────────────────────────────────────────────────────────────

# Create the GitHub OIDC Identity Provider in your AWS Account
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"] # Current GitHub thumbprints
}

# Variable to specify which GitHub repo is allowed to deploy
variable "github_repo" {
  description = "The GitHub repository allowed to deploy (e.g., username/market-analyser)"
  type        = string
  # IMPORTANT: Change this to your actual GitHub username/repo
  default     = "rnsivakumar76/market_analyser_ai"
}

# The IAM Role that GitHub Actions will assume
resource "aws_iam_role" "github_actions" {
  name = "github-actions-market-analyser"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          },
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
          }
        }
      }
    ]
  })
}

# Attach administrative privileges to this role (required for Terraform to build AWS infra)
# Note: For strict production environments, you can scope this down.
resource "aws_iam_role_policy_attachment" "github_actions_admin" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "github_actions_role_arn" {
  description = "The ARN of the IAM role for GitHub Actions to assume"
  value       = aws_iam_role.github_actions.arn
}
