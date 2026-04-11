# ─────────────────────────────────────────────
# CodeBuild - Builds user app Docker images
# ─────────────────────────────────────────────

resource "aws_iam_role" "codebuild" {
  name = "tutaia-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "tutaia-codebuild-role"
  }
}

resource "aws_iam_role_policy" "codebuild_permissions" {
  name = "tutaia-codebuild-permissions"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:CreateRepository",
          "ecr:DescribeRepositories"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::tutaia-app-uploads-${data.aws_caller_identity.current.account_id}",
          "arn:aws:s3:::tutaia-app-uploads-${data.aws_caller_identity.current.account_id}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/tutaia/*"
      }
    ]
  })
}

resource "aws_codebuild_project" "app_builder" {
  name          = "tutaia-app-builder"
  description   = "Builds Docker images from user uploaded vibe-coded apps"
  build_timeout = 20
  service_role  = aws_iam_role.codebuild.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "APP_ID"
      value = "placeholder"
    }

    environment_variable {
      name  = "S3_BUCKET"
      value = "tutaia-app-uploads-${data.aws_caller_identity.current.account_id}"
    }

    environment_variable {
      name  = "S3_KEY"
      value = "placeholder"
    }

    environment_variable {
      name  = "ECR_REPO_URL"
      value = "placeholder"
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }
  }

  source {
    type      = "NO_SOURCE"
    buildspec = <<-BUILDSPEC
      version: 0.2
      phases:
        install:
          commands:
            - echo "Installing Nixpacks..."
            - curl -sSL https://nixpacks.com/install.sh | bash
            - export PATH="$PATH:/root/.nix-profile/bin"
            - nixpacks --version
        pre_build:
          commands:
            - echo "Logging into ECR..."
            - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
            - echo "Ensuring ECR repository exists..."
            - aws ecr describe-repositories --repository-names tutaia/apps/$APP_ID --region $AWS_DEFAULT_REGION || aws ecr create-repository --repository-name tutaia/apps/$APP_ID --region $AWS_DEFAULT_REGION
            - echo "Downloading app source from S3..."
            - mkdir -p /tmp/app
            - aws s3 cp s3://$S3_BUCKET/$S3_KEY /tmp/app.zip
            - cd /tmp && unzip -o app.zip -d app
            - ls -la /tmp/app
        build:
          commands:
            - cd /tmp/app
            - echo "Normalizing app structure..."
            - if [ $(ls -d */ 2>/dev/null | wc -l) -eq 1 ] && [ $(ls -A | wc -l) -eq 1 ]; then SUBDIR=$(ls -d */ | head -1); echo "Moving contents from $SUBDIR"; mv $SUBDIR/* . 2>/dev/null || true; rmdir $SUBDIR 2>/dev/null || true; fi
            - echo "PORT=8080" >> .env 2>/dev/null || true
            - echo "Building with Nixpacks..."
            - nixpacks build . --name $APP_ID --env PORT=8080
            - docker tag $APP_ID:latest $ECR_REPO_URL:$IMAGE_TAG
        post_build:
          commands:
            - echo "Pushing image to ECR..."
            - docker push $ECR_REPO_URL:$IMAGE_TAG
            - echo "Build complete. Image $ECR_REPO_URL:$IMAGE_TAG"
    BUILDSPEC
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/tutaia/codebuild"
      stream_name = "app-builds"
      status      = "ENABLED"
    }
  }

  tags = {
    Name = "tutaia-app-builder"
  }
}

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/tutaia/codebuild"
  retention_in_days = 7

  tags = {
    Name = "tutaia-codebuild-logs"
  }
}

resource "aws_iam_role_policy" "platform_api_codebuild" {
  name = "tutaia-platform-api-codebuild"
  role = "tutaia-platform-api-task-role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "codebuild:StartBuild",
          "codebuild:BatchGetBuilds",
          "codebuild:ListBuildsForProject",
          "codebuild:StopBuild"
        ]
        Resource = aws_codebuild_project.app_builder.arn
      }
    ]
  })
}

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.app_builder.name
}

output "codebuild_role_arn" {
  description = "CodeBuild IAM role ARN"
  value       = aws_iam_role.codebuild.arn
}
