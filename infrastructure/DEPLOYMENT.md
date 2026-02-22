# 🚀 Deployment Guide — Market Analyser on AWS Lambda

### ⚡ Current Migration Status
- **Backend**: AWS Lambda + API Gateway -> **Live**
- **Frontend**: S3 Website hosting -> **Live**
- **API URL**: `https://o9dgs1ujz1.execute-api.ap-southeast-1.amazonaws.com/api`
- **Web App**: `http://market-analyser-frontend-614686365382.s3-website-ap-southeast-1.amazonaws.com`

---

## Architecture Overview

```
Internet
   │
   ▼
CloudFront (CDN + HTTPS)
   ├── /api/*  → AWS API Gateway → AWS Lambda (FastAPI backend)
   └── /*      → S3 Bucket (Angular SPA)

GitHub Actions (OIDC Authentication - ZERO AWS KEYS STORED!)
   ├── Build → Docker images
   ├── Push  → AWS ECR
   ├── Plan  → Terraform (infra changes)
   └── Deploy → Lambda Code Update + S3 sync
```

## 💰 Estimated Monthly Cost (AWS Free Tier Aware)

| Service        | Spec                         | Cost/Mo |
|----------------|------------------------------|---------|
| AWS Lambda     | 3.2M seconds free tier       | ~$0     |
| API Gateway    | 1M API calls/mo free         | ~$0     |
| CloudFront     | 1TB free/mo                  | ~$0     |
| S3             | 5GB free tier                | ~$0     |
| ECR            | 500MB free tier              | ~$0     |
| CloudWatch     | 7-day log retention          | ~$0-1   |
| **Total**      | **100% Serverless**          | **~$0/mo** |

> 💡 **Cost Tip**: AWS Lambda charges absolutely nothing when it is not running. Since we use Serverless architecture (API Gateway + Lambda), your monthly cost defaults to exactly $0.00 if you stay within the generously high AWS Free Tier limits!

---

## 🛠️ Step-by-Step Setup

### Step 1: AWS Account Prerequisites

1. Create an AWS account (or use existing)
2. Install & configure AWS CLI locally:
   ```bash
   aws configure
   # Enter: Access Key, Secret Key, Region (e.g. ap-southeast-1), Output: json
   ```

### Step 2: Bootstrap Terraform State (Run ONCE)

This creates the S3 bucket and DynamoDB table for Terraform remote state.

```bash
# Set your AWS Account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=ap-southeast-1   # Change to your preferred region

# Run the bootstrap script
chmod +x infrastructure/bootstrap.sh
./infrastructure/bootstrap.sh
```

### Step 3: Configure GitHub Repository Name for OIDC

Open `infrastructure/terraform/github_oidc.tf` and edit `var.github_repo`:

```hcl
variable "github_repo" {
  default = "YOUR_USERNAME/market-analyser"   # <--- Change this to your GitHub Repository!
}
```

### Step 4: First-Time Terraform Apply (Local)

Run Terraform manually the first time to create AWS infrastructure (including the OIDC role):

```bash
cd infrastructure/terraform

# Initialize with remote state
terraform init \
  -backend-config="bucket=market-analyser-tfstate-${AWS_ACCOUNT_ID}" \
  -backend-config="key=market-analyser/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}" \
  -backend-config="dynamodb_table=market-analyser-tf-locks" \
  -backend-config="encrypt=true"

# Apply
terraform apply \
  -var="aws_account_id=${AWS_ACCOUNT_ID}" \
  -var="aws_region=${AWS_REGION}" \
  -var="backend_image=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/market-analyser-backend:latest"
```

### Step 5: Configure GitHub Secrets / Variables

Go to your repository on GitHub:
**Settings → Secrets and variables → Actions → Variables (NOT secrets):**

| Name                    | Value                          |
|-------------------------|--------------------------------|
| `AWS_ACCOUNT_ID`        | Your 12-digit AWS account ID   |
| `AWS_REGION`            | `ap-southeast-1`               |
| `TF_STATE_BUCKET`       | `market-analyser-tfstate-XXXX` |
| `TF_LOCK_TABLE`         | `market-analyser-tf-locks`     |

*No AWS keys are needed anywhere! OIDC does the authentication securely.*

### Step 6: Create the GitHub Environment for Approvals

To prevent Terraform from automatically breaking things without your approval:
1. Go to **Settings → Environments**
2. Click **New environment**, name it exactly `production`.
3. Check the **Required reviewers** box and add yourself.

### Step 7: Push to GitHub

```bash
git add .
git commit -m "Migrate backend to Serverless AWS Lambda"
git push
```

The workflow will automatically run! For Terraform changes, it will pause and send you an email to confirm the deployment.

---

## 🌩️ Access Your App

Once GitHub Actions is done deploying, access your frontend application via CloudFront:

```bash
cd infrastructure/terraform
terraform output cloudfront_url
# → https://d1234abcd.cloudfront.net
```

---

## 🔧 Maintenance Commands

### Destroy everything (nuclear option)
```bash
cd infrastructure/terraform
terraform destroy \
  -var="aws_account_id=${AWS_ACCOUNT_ID}" \
  -var="aws_region=${AWS_REGION}" \
  -var="backend_image=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/market-analyser-backend:latest"
```
