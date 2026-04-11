from pydantic import BaseModel
from typing import Optional


class PreflightResponse(BaseModel):
    required_env_vars: list[str]
    message: str


class DeployResponse(BaseModel):
    app_id: str
    deployment_id: str
    status: str
    url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    build_logs: Optional[str] = None
    note: Optional[str] = None


class AppResponse(BaseModel):
    id: str
    name: str
    url: str
    status: str
    created_at: str


class DeploymentResponse(BaseModel):
    id: str
    status: str
    created_at: str
    deployed_at: Optional[str] = None
    error_message: Optional[str] = None
