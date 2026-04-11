# ─────────────────────────────────────────────
# ALB Security Group
# ─────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "tutaia-alb-sg"
  description = "Security group for ALB - allows HTTP and HTTPS from internet"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "tutaia-alb-sg"
  }
}

# ─────────────────────────────────────────────
# ECS Tasks Security Group
# Only accepts traffic from ALB
# ─────────────────────────────────────────────
resource "aws_security_group" "ecs_tasks" {
  name        = "tutaia-ecs-tasks-sg"
  description = "Security group for user app ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Traffic from ALB only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow any port from ALB for apps that use non-standard ports
  # Nixpacks normalises to 8080 but this is a safety net
  ingress {
    description     = "All ports from ALB"
    from_port       = 1024
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "All outbound - apps need to call external APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "tutaia-ecs-tasks-sg"
  }
}

# ─────────────────────────────────────────────
# Platform API Security Group (your deployment engine)
# ─────────────────────────────────────────────
resource "aws_security_group" "platform_api" {
  name        = "tutaia-platform-api-sg"
  description = "Security group for Tutaia platform API"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTPS from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "tutaia-platform-api-sg"
  }
}

# ─────────────────────────────────────────────
# RDS Security Group
# Only accepts traffic from ECS tasks and platform API
# ─────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "tutaia-rds-sg"
  description = "Security group for platform RDS - private access only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  ingress {
    description     = "Postgres from platform API"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.platform_api.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "tutaia-rds-sg"
  }
}
