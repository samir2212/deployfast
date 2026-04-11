from sqlalchemy import (
    create_engine, Column, String, Integer,
    DateTime, JSON, Text, Enum as SAEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from app.core.config import get_settings
import enum

Base = declarative_base()


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────
class DeploymentStatus(str, enum.Enum):
    PENDING    = "pending"     # Upload received, build not started
    BUILDING   = "building"    # Nixpacks running
    PUSHING    = "pushing"     # Pushing image to ECR
    DEPLOYING  = "deploying"   # ECS service being created/updated
    LIVE       = "live"        # App is live and healthy
    FAILED     = "failed"      # Something went wrong
    STOPPED    = "stopped"     # User stopped the app


class AppStatus(str, enum.Enum):
    ACTIVE  = "active"
    STOPPED = "stopped"
    DELETED = "deleted"


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True)  # Clerk user ID
    email           = Column(String, unique=True, nullable=False)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())


class App(Base):
    """
    Represents a user's deployed application.
    One user can have multiple apps.
    """
    __tablename__ = "apps"

    id              = Column(String, primary_key=True)   # e.g. "abc123"
    user_id         = Column(String, nullable=False)     # Clerk user ID
    name            = Column(String, nullable=False)     # User-provided name
    subdomain       = Column(String, unique=True, nullable=False)  # abc123.ai-deploy.tutaia.com
    status          = Column(SAEnum(AppStatus), default=AppStatus.ACTIVE)

    # AWS resources for this app
    ecr_repository  = Column(String)    # ECR repo URL
    ecs_service_arn = Column(String)    # ECS service ARN
    task_def_arn    = Column(String)    # Current task definition ARN
    alb_rule_arn    = Column(String)    # ALB listener rule ARN
    alb_tg_arn      = Column(String)    # ALB target group ARN
    alb_priority    = Column(Integer)   # ALB rule priority (unique per app)
    log_group       = Column(String)    # CloudWatch log group

    # App metadata
    detected_stack  = Column(String)    # "node", "python", "static" etc
    env_vars        = Column(JSON, default=dict)  # Encrypted env vars

    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Deployment(Base):
    """
    Each time a user deploys or redeploys, one record is created.
    Tracks the full lifecycle of a single deploy attempt.
    """
    __tablename__ = "deployments"

    id              = Column(String, primary_key=True)
    app_id          = Column(String, nullable=False)
    user_id         = Column(String, nullable=False)
    status          = Column(SAEnum(DeploymentStatus), default=DeploymentStatus.PENDING)

    # Build info
    image_tag       = Column(String)    # Docker image tag pushed to ECR
    detected_stack  = Column(String)    # What Nixpacks detected
    build_logs      = Column(Text)      # Nixpacks build output
    error_message   = Column(Text)      # If failed, why

    # Timing
    created_at      = Column(DateTime, server_default=func.now())
    build_started_at  = Column(DateTime)
    build_finished_at = Column(DateTime)
    deployed_at       = Column(DateTime)
    failed_at         = Column(DateTime)


# ─────────────────────────────────────────────
# Database connection
# ─────────────────────────────────────────────
def get_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,     # Detect stale connections
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory():
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for database sessions."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables. Called at startup."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
