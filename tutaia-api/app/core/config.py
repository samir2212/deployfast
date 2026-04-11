from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────
    app_name: str = "Tutaia Platform API"
    environment: str = "production"
    debug: bool = False

    # ── AWS ──────────────────────────────────────────
    aws_region: str = "eu-central-1"
    aws_account_id: str

    # ── Platform domain ──────────────────────────────
    # User apps get {app_id}.ai-deploy.tutaia.com
    platform_domain: str = "ai-deploy.tutaia.com"

    # ── ECS ──────────────────────────────────────────
    ecs_cluster_name: str = "tutaia-cluster"
    ecs_task_execution_role_arn: str
    ecs_task_role_arn: str
    ecs_tasks_security_group_id: str
    private_subnet_ids: str  # comma-separated
    # Default resources per user app - can be overridden per deploy
    default_task_cpu: int = 256
    default_task_memory: int = 512

    # ── ALB ──────────────────────────────────────────
    alb_https_listener_arn: str
    # Priority range for user app rules: 100-49999
    # Platform API rule is priority 1
    alb_rule_priority_start: int = 100

    # ── ECR ──────────────────────────────────────────
    # Base URL: {account}.dkr.ecr.{region}.amazonaws.com
    ecr_base_url: str

    # ── S3 ──────────────────────────────────────────
    uploads_bucket_name: str

    # ── Database ────────────────────────────────────
    database_url: str

    # ── Clerk Auth ──────────────────────────────────
    clerk_secret_key: str          # sk_live_... from Clerk dashboard
    clerk_publishable_key: str     # pk_live_... from Clerk dashboard
    clerk_jwks_url: str = ""       # auto-set in __init__

    # ── Nixpacks ────────────────────────────────────
    nixpacks_version: str = "1.21.0"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-construct JWKS URL from publishable key
        if not self.clerk_jwks_url:
            # Extract instance from publishable key
            # pk_live_Y2xlcmsu... → decode to get domain
            import base64
            try:
                # Clerk publishable key format: pk_live_{base64(domain)}
                encoded = self.clerk_publishable_key.split("_")[2]
                # Add padding if needed
                padding = 4 - len(encoded) % 4
                if padding != 4:
                    encoded += "=" * padding
                domain = base64.b64decode(encoded).decode("utf-8").rstrip("$")
                object.__setattr__(self, "clerk_jwks_url", f"https://{domain}/.well-known/jwks.json")
            except Exception:
                # Fallback - set manually in env if this fails
                pass

    @property
    def private_subnets(self) -> list[str]:
        return [s.strip() for s in self.private_subnet_ids.split(",")]

    @property
    def ecr_registry(self) -> str:
        return f"{self.aws_account_id}.dkr.ecr.{self.aws_region}.amazonaws.com"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
