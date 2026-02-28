# Quick CloudFront Configuration Validation
Write-Host "=== CloudFront Configuration Validation ==="

$cloudfrontFile = "infrastructure/terraform/s3_cloudfront.tf"
$content = Get-Content $cloudfrontFile

# Check for required parameters
$requiredParams = @(
    "default_cache_behavior",
    "cached_methods",
    "allowed_methods",
    "target_origin_id"
)

Write-Host "Checking required CloudFront parameters..."
foreach ($param in $requiredParams) {
    if ($content -match $param) {
        Write-Host "✅ Found: $param"
    } else {
        Write-Host "❌ Missing: $param"
    }
}

# Check for problematic compress parameter in default_cache_behavior
if ($content -match "default_cache_behavior.*compress.*true") {
    Write-Host "❌ ISSUE: 'compress = true' found in default_cache_behavior (not supported)"
    Write-Host "   This should only be in ordered_cache_behavior blocks"
} else {
    Write-Host "✅ No compress parameter in default_cache_behavior"
}

# Check cache behavior structure
$defaultBehavior = Select-String -Path $cloudfrontFile -Pattern "default_cache_behavior\s*{" -Context 0,20
if ($defaultBehavior) {
    Write-Host "`n=== Default Cache Behavior Structure ==="
    $defaultBehavior.Context.PostContext | ForEach-Object { Write-Host $_ }
}

Write-Host "`n=== Validation Complete ==="
