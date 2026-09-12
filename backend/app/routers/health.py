from fastapi import APIRouter

from app.schemas import HealthResponse

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(version=APP_VERSION)
