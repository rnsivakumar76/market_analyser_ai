# ------------------------------------------------------------------------------
# S3 Bucket  Angular Frontend Static Hosting (PER-ENVIRONMENT)
# ------------------------------------------------------------------------------

locals {
  env_suffix = var.environment == "production" ? "" : "-${var.environment}"
}

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.app_name}-frontend${local.env_suffix}-${var.aws_account_id}"
  force_destroy = true

  tags = {
    Name        = "${var.app_name}-frontend-${var.environment}"
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# S3 Bucket  Application Configuration persistence (PER-ENVIRONMENT)
# ------------------------------------------------------------------------------
resource "aws_s3_bucket" "config" {
  bucket = "${var.app_name}-config${local.env_suffix}-${var.aws_account_id}"

  tags = {
    Name        = "${var.app_name}-config-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document { suffix = "index.html" }
  error_document { key    = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend_public" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}



# ------------------------------------------------------------------------------
# CloudFront  HTTPS & Content Delivery - Force Recreation
# ------------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_identity" "origin" {
  comment = "Origin access identity for CloudFront distribution"
}

resource "aws_cloudfront_distribution" "frontend_new" {

  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "s3-origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.origin.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
