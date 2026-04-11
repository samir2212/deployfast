# ─────────────────────────────────────────────
# ECR - Base repository for platform API image
# User app repos are created dynamically by the
# platform API when a new app is deployed
# ─────────────────────────────────────────────
resource "aws_ecr_repository" "platform_api" {
  name                 = "tutaia/platform-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "tutaia-platform-api-ecr"
  }
}

resource "aws_ecr_lifecycle_policy" "platform_api" {
  repository = aws_ecr_repository.platform_api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ─────────────────────────────────────────────
# S3 Bucket - User App Uploads
# Users upload their zip files here
# Platform API reads from here to trigger builds
# ─────────────────────────────────────────────
resource "aws_s3_bucket" "uploads" {
  bucket = "tutaia-app-uploads-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "tutaia-app-uploads"
  }
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access - uploads are private
resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Auto-delete uploaded zips after 24h
# Once built into a Docker image they're not needed
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "delete-old-uploads"
    status = "Enabled"

    filter {}

    expiration {
      days = 1
    }
  }
}

# ─────────────────────────────────────────────
# Get current AWS account ID
# ─────────────────────────────────────────────
data "aws_caller_identity" "current" {}

# ─────────────────────────────────────────────
# CloudWatch Log Groups
# One group per app, platform API creates them
# dynamically. This creates the root group.
# ─────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "apps_root" {
  name              = "/tutaia/apps"
  retention_in_days = 7 # Keep app logs 7 days - enough for validation

  tags = {
    Name = "tutaia-apps-logs"
  }
}
