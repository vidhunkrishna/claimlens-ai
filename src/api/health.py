from datetime import datetime, timezone
from fastapi import APIRouter
from src.models.schemas import HealthResponse
from src.core.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def get_health():
    """
    Health check endpoint to verify backend operational status.
    """
    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
