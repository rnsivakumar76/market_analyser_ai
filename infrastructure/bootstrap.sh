#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap Script — Run ONCE by hand to create Terraform state infrastructure
# This creates the S3 bucket and DynamoDB table that Terraform needs to store
# its state file. After this you never need to run it again.
#
# Prerequisites:
#   1. AWS CLI installed and configured (aws configure)
#   2. Your AWS account ID set as an environment variable:
#      export AWS_ACCOUNT_ID=123456789012
#      export AWS_REGION=ap-southeast-1
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-southeast-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?Please set AWS_ACCOUNT_ID}"
APP_NAME="market-analyser"

TF_STATE_BUCKET="${APP_NAME}-tfstate-${AWS_ACCOUNT_ID}"
TF_LOCK_TABLE="${APP_NAME}-tf-locks"

echo "🚀 Bootstrapping Terraform state infrastructure..."
echo "   Region  : $AWS_REGION"
echo "   Account : $AWS_ACCOUNT_ID"
echo "   Bucket  : $TF_STATE_BUCKET"
echo "   Table   : $TF_LOCK_TABLE"
echo ""

# ── S3 Bucket for Terraform state ────────────────────────────────────────────
if aws s3api head-bucket --bucket "$TF_STATE_BUCKET" 2>/dev/null; then
  echo "✅ S3 bucket already exists: $TF_STATE_BUCKET"
else
  echo "📦 Creating S3 state bucket..."
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket \
      --bucket "$TF_STATE_BUCKET" \
      --region "$AWS_REGION"
  else
    aws s3api create-bucket \
      --bucket "$TF_STATE_BUCKET" \
      --region "$AWS_REGION" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION"
  fi

  # Enable versioning (allows state recovery)
  aws s3api put-bucket-versioning \
    --bucket "$TF_STATE_BUCKET" \
    --versioning-configuration Status=Enabled

  # Enable encryption
  aws s3api put-bucket-encryption \
    --bucket "$TF_STATE_BUCKET" \
    --server-side-encryption-configuration '{
      "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }'

  # Block all public access
  aws s3api put-public-access-block \
    --bucket "$TF_STATE_BUCKET" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  echo "✅ S3 state bucket created: $TF_STATE_BUCKET"
fi

# ── DynamoDB Table for state locking ─────────────────────────────────────────
if aws dynamodb describe-table --table-name "$TF_LOCK_TABLE" --region "$AWS_REGION" 2>/dev/null; then
  echo "✅ DynamoDB lock table already exists: $TF_LOCK_TABLE"
else
  echo "🔒 Creating DynamoDB lock table..."
  aws dynamodb create-table \
    --table-name "$TF_LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION"
  echo "✅ DynamoDB lock table created: $TF_LOCK_TABLE"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "✅ Bootstrap complete! Add these to GitLab CI/CD Variables:"
echo "   TF_STATE_BUCKET = $TF_STATE_BUCKET"
echo "   TF_LOCK_TABLE   = $TF_LOCK_TABLE"
echo "   AWS_REGION      = $AWS_REGION"
echo "   AWS_ACCOUNT_ID  = $AWS_ACCOUNT_ID"
echo ""
echo "   AWS_ACCESS_KEY_ID     = (from Terraform output after first apply)"
echo "   AWS_SECRET_ACCESS_KEY = (from Terraform output after first apply)"
echo "═══════════════════════════════════════════════════════"
