# ─────────────────────────────────────────────
# RDS Subnet Group
# RDS lives in private subnets only
# ─────────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "tutaia-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "tutaia-db-subnet-group"
  }
}

# ─────────────────────────────────────────────
# RDS Postgres - Platform Database
# Stores: users, deployments, app metadata,
#         subdomain mappings, env vars (encrypted)
# ─────────────────────────────────────────────
resource "aws_db_instance" "platform" {
  identifier = "tutaia-platform-db"

  engine         = "postgres"
  engine_version = "17.4"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100 # Auto-scaling storage up to 100GB
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Private - no public access
  publicly_accessible = false

  # Backups - keep 7 days during validation
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # Don't delete DB if you accidentally run terraform destroy
  deletion_protection = false # Set to true after validation phase
  skip_final_snapshot = true  # Set to false after validation phase

  # Performance Insights for free tier (7 days retention)
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  # Parameter group for Postgres 17
  parameter_group_name = aws_db_parameter_group.postgres17.name

  tags = {
    Name = "tutaia-platform-db"
  }
}

resource "aws_db_parameter_group" "postgres17" {
  family = "postgres17"
  name   = "tutaia-postgres17"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Name = "tutaia-postgres17-params"
  }
}

# ─────────────────────────────────────────────
# Store DB connection string in SSM Parameter Store
# Platform API reads this at startup
# ─────────────────────────────────────────────
resource "aws_ssm_parameter" "db_url" {
  name  = "/tutaia/platform/database_url"
  type  = "SecureString"
  value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.platform.endpoint}/${var.db_name}"

  tags = {
    Name = "tutaia-db-url"
  }
}
