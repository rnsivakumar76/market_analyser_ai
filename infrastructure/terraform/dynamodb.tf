# ──────────────────────────────────────────────────────────────────────────────
# DynamoDB — Single-Table Design for NEXUS
# Free Tier: 25 GB storage + 25 RCU/WCU (always free, not 12-month limited)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "nexus" {
  name         = "nexus-${var.environment}"
  billing_mode = "PAY_PER_REQUEST" # On-demand: only pay for what you use ($0 at low traffic)
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI for querying by type across all users (e.g. "all trades today")
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # Auto-delete old alert logs after 30 days (TTL)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false # Keep disabled for free tier
  }

  tags = {
    Name        = "nexus-${var.environment}"
    Environment = var.environment
    App         = var.app_name
  }
}
