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

resource "aws_cloudfront_distribution" "frontend_fixed" {

  enabled             = true
  default_root_object = "index.html"

  # S3 Origin for static frontend files
  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "s3-origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.origin.cloudfront_access_identity_path
    }
  }

  # API Gateway Origin for backend API calls
  origin {
    domain_name = replace(aws_apigatewayv2_api.http_api.api_endpoint, "/^https?://([^/]+).*/", "$1")
    origin_id   = "api-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # API Behavior - HIGHER PRECEDENCE
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods          = ["GET", "HEAD"]
    target_origin_id        = "api-origin"
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "Referer", "X-Forwarded-Host", "X-Forwarded-Proto", "Content-Type", "Accept"]
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  # Default behavior for S3 static content - LOWER PRECEDENCE
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
