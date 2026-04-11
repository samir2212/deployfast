# Tutaia Platform API

FastAPI service that handles all deployments.
Receives user zip uploads, triggers CodeBuild, creates ECS services, returns live URLs.

## Project Structure

```
tutaia-api/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings + SSM secrets loader
│   ├── database.py          # Async SQLAlchemy setup
│   ├── models/
│   │   └── models.py        # User and App database models
│   ├── middleware/
│   │   └── auth.py          # Clerk JWT verification
│   ├── routers/
│   │   ├── health.py        # /health endpoint
│   │   ├── auth.py          # /api/auth endpoints
│   │   └── apps.py          # /api/apps endpoints
│   └── services/
│       ├── preflight.py     # Zip scanner - detects env vars, stack
│       ├── aws.py           # All AWS operations (ECS, ALB, CodeBuild, S3)
│       └── deployment.py    # Deployment orchestration
├── Dockerfile
├── requirements.txt
├── build_and_push.sh        # Build + push to ECR
└── deploy_platform_api.py   # Deploy to ECS
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | ALB health check |
| GET | /api/auth/config | Returns Clerk publishable key |
| GET | /api/auth/me | Current user profile |
| POST | /api/apps/scan | Pre-flight scan zip (call before deploy) |
| POST | /api/apps/ | Deploy new app |
| POST | /api/apps/{id}/redeploy | Redeploy with new code |
| GET | /api/apps/ | List user's apps |
| GET | /api/apps/{id} | Get app details |
| GET | /api/apps/{id}/status | Poll deployment status |
| GET | /api/apps/{id}/logs | Get app logs |
| DELETE | /api/apps/{id} | Delete app |

## Deployment Flow

```
POST /api/apps/
  1. Pre-flight scan zip
  2. Upload zip to S3
  3. Create App record (status: building)
  4. Trigger CodeBuild (Nixpacks build)
  5. Wait for build (~2-4 min)
  6. Create ALB target group
  7. Create ALB listener rule (host-header routing)
  8. Register ECS task definition
  9. Create ECS Fargate service
  10. Return app with live URL
```

## Prerequisites

Before deploying, ensure:
1. Terraform infrastructure is applied (tutaia-infra/)
2. Clerk keys are in SSM:
   - /tutaia/platform/clerk_secret_key
   - /tutaia/platform/clerk_publishable_key
3. Database URL is in SSM:
   - /tutaia/platform/database_url
4. Docker is running locally
5. AWS CLI is configured

## Deploy to Production

### Step 1: Build and push Docker image
```bash
chmod +x build_and_push.sh
./build_and_push.sh
```

### Step 2: Deploy to ECS
```bash
python deploy_platform_api.py
```

### Step 3: Verify
```bash
# Check service is running
aws ecs describe-services \
  --cluster tutaia-cluster \
  --services tutaia-platform-api \
  --region eu-central-1 \
  --query "services[0].{status:status,running:runningCount,desired:desiredCount}"

# Test health endpoint
curl https://api.ai-deploy.tutaia.com/health

# Test API docs
open https://api.ai-deploy.tutaia.com/docs
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set AWS profile (needs access to SSM for secrets)
export AWS_PROFILE=your-profile
export AWS_DEFAULT_REGION=eu-central-1

# Run locally
uvicorn app.main:app --reload --port 3000
```

Note: Local dev still reads secrets from SSM.
Ensure your local AWS credentials have SSM read access.

## Monitoring

```bash
# Tail platform API logs
aws logs tail /tutaia/platform-api --follow --region eu-central-1

# Tail a specific user app logs
aws logs tail /tutaia/apps/{app_id} --follow --region eu-central-1

# Tail CodeBuild logs
aws logs tail /tutaia/codebuild --follow --region eu-central-1
```

## Debugging

### ECS Exec into running container
```bash
aws ecs execute-command \
  --cluster tutaia-cluster \
  --task $(aws ecs list-tasks --cluster tutaia-cluster --service-name tutaia-platform-api --query "taskArns[0]" --output text) \
  --container platform-api \
  --interactive \
  --command "/bin/bash" \
  --region eu-central-1
```

### Common Issues

**Health check failing:**
Check logs - most likely SSM parameter not found or DB connection failed.

**Build timeout:**
CodeBuild default is 20 min. Nixpacks on large repos can be slow.
Check /tutaia/codebuild log group.

**ECS task not starting:**
Check task stopped reason:
```bash
aws ecs describe-tasks \
  --cluster tutaia-cluster \
  --tasks $(aws ecs list-tasks --cluster tutaia-cluster --service-name tutaia-app-{id} --query "taskArns[0]" --output text) \
  --region eu-central-1 \
  --query "tasks[0].stoppedReason"
```
