variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Root domain name"
  type        = string
  default     = "tutaia.com"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["eu-central-1a", "eu-central-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Platform database name"
  type        = string
  default     = "tutaia_platform"
}

variable "db_username" {
  description = "Platform database username"
  type        = string
  default     = "tutaia_admin"
}

variable "db_password" {
  description = "Platform database password - change this before applying"
  type        = string
  sensitive   = true
  # Set via: export TF_VAR_db_password="your-strong-password"
}

variable "platform_subdomain" {
  description = "Platform subdomain prefix"
  type        = string
  default     = "ai-deploy"
}

variable "ecs_task_cpu" {
  description = "Default CPU for user app ECS tasks (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "ecs_task_memory" {
  description = "Default memory for user app ECS tasks (MB)"
  type        = number
  default     = 512
}

variable "bastion_public_key" {
  description = "Public SSH key for bastion host"
  type        = string
}
