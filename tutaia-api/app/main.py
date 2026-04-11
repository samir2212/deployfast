import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import apps, auth, health, payments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Tutaia Platform API...")
    settings = get_settings()
    logger.info(f"Region: {settings.aws_region}")
    logger.info(f"Domain: {settings.platform_domain}")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Tutaia Platform API...")


app = FastAPI(
    title="Tutaia Platform API",
    description="Deploy vibe-coded apps in 60 seconds",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-deploy.tutaia.com",
        "https://deployfast.tutaia.com",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/auth")
app.include_router(apps.router, prefix="/api/apps")
app.include_router(payments.router, prefix="/api/payments")
