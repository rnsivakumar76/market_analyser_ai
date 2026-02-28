#!/bin/bash

# Terraform Local Testing Script
echo "=== Terraform Local Testing ==="

# Navigate to terraform directory
cd infrastructure/terraform

echo "1. Checking Terraform format..."
terraform fmt -check -diff
if [ $? -ne 0 ]; then
    echo "❌ Format check failed. Run 'terraform fmt' to fix."
    exit 1
fi

echo "2. Validating Terraform configuration..."
terraform validate
if [ $? -ne 0 ]; then
    echo "❌ Validation failed."
    exit 1
fi

echo "3. Initializing Terraform..."
terraform init
if [ $? -ne 0 ]; then
    echo "❌ Init failed."
    exit 1
fi

echo "4. Creating execution plan (dry run)..."
terraform plan -detailed-exitcode
PLAN_EXIT_CODE=$?

if [ $PLAN_EXIT_CODE -eq 0 ]; then
    echo "✅ No changes detected."
elif [ $PLAN_EXIT_CODE -eq 1 ]; then
    echo "❌ Plan failed."
    exit 1
elif [ $PLAN_EXIT_CODE -eq 2 ]; then
    echo "✅ Changes detected (plan successful)."
    echo "Review the plan above, then run 'terraform apply' if approved."
fi

echo "=== Testing Complete ==="
