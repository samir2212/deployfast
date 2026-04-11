# Tutaia Platform — AWS Infrastructure (Terraform)

This document covers provisioning the full AWS stack for DeployFast with Terraform.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Terraform `>= 1.5.0` | `brew install terraform` or use [tfenv](https://github.com/tfutils/tfenv) |
| AWS CLI v2 | Configured with credentials that have broad admin permissions |
| Route 53 hosted zone | `tutaia.com` zone must already exist before applying |
| S3 state bucket | `tutaia-terraform-state-file` must exist in `eu-central-1` |

---

## Getting Started

### 1. Verify Route 53 hosted zone

```bash
aws route53 list-hosted-zones --query "HostedZones[?Name=='tutaia.com.']"
```

### 2. Verify Terraform state bucket

```bash
aws s3 ls s3://tutaia-terraform-state-file --region eu-central-1
```

### 3. Set required secrets via environment variables

```bash
export TF_VAR_db_password="choose-a-strong-password"
export TF_VAR_bastion_public_key="$(cat ~/.ssh/id_rsa.pub)"
```

> **Never** put these values inside a `.tfvars` file that could accidentally be committed.

### 4. Copy and review variable defaults

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars if you need non-default values
```

### 5. Initialise Terraform

```bash
terraform init
```

### 6. Preview the plan

```bash
terraform plan
```

Expect ~35 resources to be created. Review carefully — real AWS resources will incur charges.

### 7. Apply

```bash
terraform apply
```

Type `yes` when prompted. Allow **10–15 minutes** — RDS takes ~8 min and ACM DNS validation takes 2–5 min.

### 8. Save outputs

```bash
terraform output -json > ../tutaia-outputs.json
```

---

## Architecture

```
                        ┌──────────────────────────────────────────────────────┐
                        │                   AWS (eu-central-1)                 │
                        │                                                      │
  User browser          │   CloudFront ──► S3 (frontend)                      │
       │                │                                                      │
       └──► tutaia.com  │   Route 53                                           │
       └──► ai-deploy.* │      │                                               │
                        │      ▼                                               │
                        │   ALB (HTTPS 443)                                    │
                        │    ├── /api*  ──► Platform API (ECS Fargate)         │
                        │    └── <app-id>.ai-deploy.tutaia.com                 │
                        │             ──► User App (ECS Fargate, per app)      │
                        │                                                      │
                        │   CodeBuild ──► ECR ──► ECS task definitions         │
                        │   S3 (uploads) ──► CodeBuild (zip → Docker image)   │
                        │   RDS PostgreSQL (private subnet)                    │
                        │   SSM Parameter Store (secrets)                     │
                        └──────────────────────────────────────────────────────┘
```

### Terraform files

| File | What it provisions |
|---|---|
| `vpc.tf` | VPC, subnets (2 AZs), IGW, NAT Gateway, route tables |
| `ecs.tf` | ECS cluster, IAM roles, platform API task definition |
| `alb.tf` | ALB, HTTPS listener, HTTP→HTTPS redirect |
| `codebuild.tf` | CodeBuild project (Nixpacks builder), IAM |
| `ecr_s3.tf` | ECR repo, S3 uploads bucket |
| `rds.tf` | PostgreSQL RDS, subnet group, SSM parameter |
| `dns_acm.tf` | Route 53 records, wildcard ACM certificate |
| `frontend.tf` | S3 + CloudFront for React frontend |
| `security_groups.tf` | ALB, ECS, RDS, bastion security groups |
| `bastion.tf` | Bastion EC2 for SSH tunnels |
| `outputs.tf` | All ARNs / IDs consumed by the platform API |

---

## Estimated Monthly Cost (validation phase)

| Resource | Approx. cost |
|---|---|
| ALB | ~$20 / month |
| RDS `db.t3.micro` | ~$15 / month |
| NAT Gateway | ~$35 / month |
| ECS Fargate (user apps) | Pay-per-use |
| ECR | ~$1 / month |
| S3 | ~$1 / month |
| Route 53 | ~$1 / month |
| CloudFront | ~$1 / month |
| **Total (fixed)** | **~$74 / month** |

> NAT Gateway dominates. Consider VPC endpoints for ECR/S3 after the validation phase.

---

## Useful Commands

### SSH into a running ECS task

```bash
aws ecs execute-command \
  --cluster tutaia-cluster \
  --task <task-id> \
  --container <container-name> \
  --interactive \
  --command "/bin/sh"
```

### Tail application logs

```bash
aws logs tail /tutaia/apps/<app-id> --follow
```

### SSH tunnel to RDS via bastion

```bash
BASTION_IP=$(terraform output -raw bastion_public_ip)
ssh -N -L 5432:<RDS_ENDPOINT>:5432 ec2-user@$BASTION_IP
# psql -h localhost -U tutaia_admin -d tutaia_platform
```

---

## Teardown

```bash
terraform destroy
```

> **Warning:** Deletes everything including the RDS database.  
> `deletion_protection = false` is intentional during the validation phase.
