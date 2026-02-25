# ──────────────────────────────────────────────────────────────────────────────
# GitHub OIDC Setup — SHARED across all environments
# Only created in the production (primary) workspace.
# Dev workspace references the existing provider and role via data sources.
# ──────────────────────────────────────────────────────────────────────────────

variable "github_repo" {
  description = "The GitHub repository allowed to deploy (e.g., username/market-analyser)"
  type        = string
  default     = "rnsivakumar76/market_analyser_ai"
}

# ─── Production: Create OIDC + Role ──────────────────────────────

resource "aws_iam_openid_connect_provider" "github" {
  count           = local.is_primary ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}

resource "aws_iam_role" "github_actions" {
  count = local.is_primary ? 1 : 0
  name  = "github-actions-market-analyser"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = aws_iam_openid_connect_provider.github[0].arn
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

resource "aws_iam_role_policy_attachment" "github_actions_admin" {
  count      = local.is_primary ? 1 : 0
  role       = aws_iam_role.github_actions[0].name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# ─── Dev: Reference existing role via data source ─────────────────

data "aws_iam_role" "github_actions" {
  count = local.is_primary ? 0 : 1
  name  = "github-actions-market-analyser"
}

locals {
  github_actions_role_arn = local.is_primary ? aws_iam_role.github_actions[0].arn : data.aws_iam_role.github_actions[0].arn
}

output "github_actions_role_arn" {
  description = "The ARN of the IAM role for GitHub Actions to assume"
  value       = local.github_actions_role_arn
}
