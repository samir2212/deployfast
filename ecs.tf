# ─────────────────────────────────────────────
# ECS Cluster
# All user app tasks run here
# ─────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "tutaia-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "tutaia-cluster"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ─────────────────────────────────────────────
# ECS Task Execution Role
# Allows ECS to pull images from ECR and write logs
# Every user app task uses this role
# ─────────────────────────────────────────────
resource "aws_iam_role" "ecs_task_execution" {
  name = "tutaia-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "tutaia-ecs-task-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow ECS to pull from any ECR repo in this account
resource "aws_iam_role_policy" "ecs_ecr_access" {
  name = "tutaia-ecs-ecr-access"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/tutaia/apps/*"
      }
    ]
  })
}

# ─────────────────────────────────────────────
# ECS Task Role
# What the running container itself can do
# Minimal permissions - apps don't need AWS access
# ─────────────────────────────────────────────
resource "aws_iam_role" "ecs_task" {
  name = "tutaia-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "tutaia-ecs-task-role"
  }
}

# Allow ECS Exec for debugging (SSM)
resource "aws_iam_role_policy" "ecs_task_ssm" {
  name = "tutaia-ecs-task-ssm"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# ─────────────────────────────────────────────
# Platform API ECS Task Definition
# Your deployment engine running on ECS
# ─────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "platform_api" {
  name              = "/tutaia/platform-api"
  retention_in_days = 30

  tags = {
    Name = "tutaia-platform-api-logs"
  }
}

# ─────────────────────────────────────────────
# IAM Role for Platform API
# Needs to manage ECS, ECR, ALB, CloudWatch
# ─────────────────────────────────────────────
resource "aws_iam_role" "platform_api_task" {
  name = "tutaia-platform-api-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "platform_api_permissions" {
  name = "tutaia-platform-api-permissions"
  role = aws_iam_role.platform_api_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Manage user app ECS services and task definitions
        Effect = "Allow"
        Action = [
          "ecs:RegisterTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:CreateService",
          "ecs:UpdateService",
          "ecs:DeleteService",
          "ecs:DescribeServices",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTaskDefinition",
          "ecs:ListTaskDefinitions",
          "ecs:TagResource"
        ]
        Resource = "*"
      },
      {
        # Create and manage ECR repositories for user apps
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository",
          "ecr:DeleteRepository",
          "ecr:DescribeRepositories",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        # Manage ALB listener rules and target groups
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:CreateTargetGroup",
          "elasticloadbalancing:DeleteTargetGroup",
          "elasticloadbalancing:CreateRule",
          "elasticloadbalancing:DeleteRule",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeRules",
          "elasticloadbalancing:ModifyRule",
          "elasticloadbalancing:RegisterTargets",
          "elasticloadbalancing:DeregisterTargets",
          "elasticloadbalancing:AddTags",
          "elasticloadbalancing:RemoveTags",
          "elasticloadbalancing:DescribeTags",
          "elasticloadbalancing:ModifyTargetGroup",
          "elasticloadbalancing:DescribeTargetHealth",
          "elasticloadbalancing:DescribeListeners"
        ]
        Resource = "*"
      },
      {
        # Read app logs for the status page
        Effect = "Allow"
        Action = [
          "logs:GetLogEvents",
          "logs:FilterLogEvents",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      },
      {
        # Pass IAM roles to ECS tasks
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      },
      {
        # Read uploaded zips from S3
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:PutObject"

        ]
        Resource = [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
      },
      {
        # SSM Parameter Store - read app secrets
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/tutaia/platform/*"
      },
      {
        # SSM for debugging
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}
