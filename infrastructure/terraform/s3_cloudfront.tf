# ------------------------------------------------------------------------------
# S3 Bucket  Angular Frontend Static Hosting (PER-ENVIRONMENT)
# ------------------------------------------------------------------------------

locals {
  env_suffix = var.environment == "production" ? "" : "-${var.environment}"
}

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.app_name}-frontend${local.env_suffix}-${var.aws_account_id}"

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
# CloudFront  HTTPS & Content Delivery
# ------------------------------------------------------------------------------
resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint
    origin_id   = "S3WebsiteOrigin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Origin for API Gateway
  origin {
    domain_name = replace(aws_apigatewayv2_api.http_api.api_endpoint, "/^https?://([^/]+).*/", "$1")
    origin_id   = "APIGatewayOrigin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  is_ipv6_enabled    = true
  default_root_object = "index.html"

  # Support Angular SPA routing: Redirect 404/403 to index.html
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
  }

  # API Behavior (No caching, passing everything) - HIGHER PRECEDENCE
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    CachedMethods          = ["GET", "HEAD"]
    target_origin_id        = "APIGatewayOrigin"
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

  # OAuth callback specific behavior - HIGHEST PRECEDENCE
  ordered_cache_behavior {
    path_pattern           = "/api/auth/callback"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    CachedMethods          = []
    target_origin_id        = "APIGatewayOrigin"
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "Referer", "X-Forwarded-Host", "X-Forwarded-Proto", "Content-Type", "Accept", "User-Agent", "Set-Cookie"]
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
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    CachedMethods          = ["GET", "HEAD"]
    target_origin_id       = "S3WebsiteOrigin"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  aliases = var.domain_name != "" ? [var.domain_name] : []

  viewer_certificate {
    cloudfront_default_certificate = var.acm_certificate_arn == "" ? true : null
    acm_certificate_arn            = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
    ssl_support_method             = var.acm_certificate_arn != "" ? "sni-only" : null
    minimum_protocol_version       = var.acm_certificate_arn != "" ? "TLSv1.2_2021" : null
  }

  tags = {
    Name        = "${var.app_name}-cloudfront"
    Environment = var.environment
  }
}
