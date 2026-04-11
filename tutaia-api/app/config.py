import boto3
import logging
from functools import lru_cache
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def get_ssm_parameter(name: str, region: str = "eu-central-1") -> str:
    """
    Reads a SecureString parameter from AWS SSM Parameter Store.
    This is how all secrets are loaded - never from env vars or code.
    """
    try:
        client = boto3.client("ssm", region_name=region)
        response = client.get_parameter(Name=name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to load SSM parameter {name}: {e}")
        raise RuntimeError(f"Cannot load required secret: {name}") from e


class Settings(BaseSettings):
    # AWS
    aws_region: str = "eu-central-1"
    aws_account_id: str = "856930835134"

    # Platform
    platform_domain: str = "ai-deploy.tutaia.com"
    platform_subdomain: str = "ai-deploy"
    root_domain: str = "tutaia.com"

    # ECS / Infra (from Terraform outputs)
    ecs_cluster_name: str = "tutaia-cluster"
    alb_https_listener_arn: str = "arn:aws:elasticloadbalancing:eu-central-1:856930835134:listener/app/tutaia-alb/ea1da746f8f7c721/5720a2ad4fb82001"
    ecs_task_execution_role_arn: str = "arn:aws:iam::856930835134:role/tutaia-ecs-task-execution-role"
    ecs_task_role_arn: str = "arn:aws:iam::856930835134:role/tutaia-ecs-task-role"
    ecs_tasks_security_group_id: str = "sg-07ae242b61f061806"
    private_subnet_ids: str = "subnet-088505349ecd7387a,subnet-03ac7243e6039bfff"
    uploads_bucket_name: str = "tutaia-app-uploads-856930835134"
    codebuild_project_name: str = "tutaia-app-builder"

    # ECS task defaults per user app
    ecs_task_cpu: int = 256
    ecs_task_memory: int = 512

    # ALB listener rule priority range for user apps
    # 1 = platform API, 2-999 = user apps
    alb_rule_priority_start: int = 10
    alb_rule_priority_end: int = 999

    # Loaded from SSM at runtime - not stored here
    _database_url: str = ""
    _clerk_secret_key: str = ""
    _clerk_publishable_key: str = ""
    _stripe_secret_key: str = ""
    _stripe_starter_price_id: str = ""
    _stripe_builder_price_id: str = ""
    _resend_api_key: str = ""

    class Config:
        env_prefix = "TUTAIA_"

    def load_secrets(self):
        """Load all secrets from SSM. Called once at startup."""
        logger.info("Loading secrets from SSM Parameter Store...")
        self._database_url = get_ssm_parameter(
            "/tutaia/platform/database_url",
            self.aws_region
        )
        self._clerk_secret_key = get_ssm_parameter(
            "/tutaia/platform/clerk_secret_key",
            self.aws_region
        )
        self._clerk_publishable_key = get_ssm_parameter(
            "/tutaia/platform/clerk_publishable_key",
            self.aws_region
        )
        logger.info("All secrets loaded from SSM successfully")

    @property
    def database_url(self) -> str:
        if not self._database_url:
            self._database_url = get_ssm_parameter(
                "/tutaia/platform/database_url",
                self.aws_region
            )
        return self._database_url

    @property
    def clerk_secret_key(self) -> str:
        if not self._clerk_secret_key:
            self._clerk_secret_key = get_ssm_parameter(
                "/tutaia/platform/clerk_secret_key",
                self.aws_region
            )
        return self._clerk_secret_key

    @property
    def clerk_publishable_key(self) -> str:
        if not self._clerk_publishable_key:
            self._clerk_publishable_key = get_ssm_parameter(
                "/tutaia/platform/clerk_publishable_key",
                self.aws_region
            )
        return self._clerk_publishable_key

    @property
    def stripe_secret_key(self) -> str:
        if not self._stripe_secret_key:
            self._stripe_secret_key = get_ssm_parameter(
                "/tutaia/platform/stripe_secret_key",
                self.aws_region
            )
        return self._stripe_secret_key

    @property
    def stripe_starter_price_id(self) -> str:
        if not self._stripe_starter_price_id:
            self._stripe_starter_price_id = get_ssm_parameter(
                "/tutaia/platform/stripe_starter_price_id",
                self.aws_region
            )
        return self._stripe_starter_price_id

    @property
    def stripe_builder_price_id(self) -> str:
        if not self._stripe_builder_price_id:
            self._stripe_builder_price_id = get_ssm_parameter(
                "/tutaia/platform/stripe_builder_price_id",
                self.aws_region
            )
        return self._stripe_builder_price_id

    @property
    def resend_api_key(self) -> str:
        if not self._resend_api_key:
            self._resend_api_key = get_ssm_parameter(
                "/tutaia/platform/resend_api_key",
                self.aws_region
            )
        return self._resend_api_key

    @property
    def private_subnets(self) -> list[str]:
        return self.private_subnet_ids.split(",")

    @property
    def ecr_base_url(self) -> str:
        return f"{self.aws_account_id}.dkr.ecr.{self.aws_region}.amazonaws.com"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
