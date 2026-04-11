from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """ALB health check endpoint. Must return 200."""
    return {"status": "healthy", "service": "tutaia-platform-api"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Tutaia Platform API",
        "version": "0.1.0",
        "docs": "/docs",
    }
