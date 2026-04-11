# ─────────────────────────────────────────────
# Outputs - values you'll need for the platform API
# Run: terraform output after applying
# ─────────────────────────────────────────────

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.main.arn
}

output "alb_https_listener_arn" {
  description = "HTTPS listener ARN - platform API uses this to add user app rules"
  value       = aws_lb_listener.https.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}

output "platform_api_task_role_arn" {
  description = "Platform API task role ARN"
  value       = aws_iam_role.platform_api_task.arn
}

output "platform_api_ecr_url" {
  description = "Platform API ECR repository URL"
  value       = aws_ecr_repository.platform_api.repository_url
}

output "uploads_bucket_name" {
  description = "S3 uploads bucket name"
  value       = aws_s3_bucket.uploads.bucket
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.platform.endpoint
  sensitive   = true
}

output "rds_db_name" {
  description = "RDS database name"
  value       = aws_db_instance.platform.db_name
}

output "db_url_ssm_parameter" {
  description = "SSM parameter name for database URL"
  value       = aws_ssm_parameter.db_url.name
}

output "ecs_tasks_security_group_id" {
  description = "Security group ID for user app ECS tasks"
  value       = aws_security_group.ecs_tasks.id
}

output "platform_api_security_group_id" {
  description = "Security group ID for platform API"
  value       = aws_security_group.platform_api.id
}

output "platform_api_target_group_arn" {
  description = "Platform API ALB target group ARN"
  value       = aws_lb_target_group.platform_api.arn
}

output "acm_certificate_arn" {
  description = "Wildcard ACM certificate ARN"
  value       = aws_acm_certificate_validation.wildcard.certificate_arn
}

output "domain_name" {
  description = "Domain name"
  value       = var.domain_name
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# ─────────────────────────────────────────────
# Frontend (S3 + CloudFront)
# ─────────────────────────────────────────────
output "frontend_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation"
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://${local.frontend_domain}"
}

output "bastion_public_ip" {
  description = "Bastion host public IP for SSH tunnel"
  value       = aws_instance.bastion.public_ip
}
