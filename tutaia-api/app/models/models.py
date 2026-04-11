import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Enum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeploymentStatus(str, PyEnum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(255), primary_key=True
    )  # Clerk user ID
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    apps: Mapped[list["App"]] = relationship("App", back_populates="user")


class App(Base):
    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())[:8],  # Short ID for subdomain
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # AWS resource references
    ecr_repo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    ecs_service_name: Mapped[str] = mapped_column(String(255), nullable=True)
    ecs_task_definition_arn: Mapped[str] = mapped_column(String(500), nullable=True)
    alb_target_group_arn: Mapped[str] = mapped_column(String(500), nullable=True)
    alb_listener_rule_arn: Mapped[str] = mapped_column(String(500), nullable=True)
    alb_rule_priority: Mapped[int] = mapped_column(Integer, nullable=True)

    # Build tracking
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, create_type=False), default=DeploymentStatus.PENDING
    )
    codebuild_build_id: Mapped[str] = mapped_column(String(255), nullable=True)
    image_tag: Mapped[str] = mapped_column(String(255), nullable=True)

    # User's env vars (stored as JSON, values encrypted at rest by RDS)
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)

    # Detected env vars from pre-flight scan
    required_env_vars: Mapped[list] = mapped_column(JSON, default=list)

    # Error details if deployment failed
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    last_deployed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="apps")

    @property
    def url(self) -> str:
        return f"https://{self.subdomain}"

    @property
    def is_running(self) -> bool:
        return self.status == DeploymentStatus.RUNNING


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id"), nullable=False
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    stripe_checkout_session_id: Mapped[str] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)  # "starter" or "builder"
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, canceled, past_due
    app_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )