from fastapi import APIRouter, Response

from app.database import get_profile
from app.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Liveness — no I/O, must stay fast and always-200 (plan.md §21)."""
    return HealthResponse(version=APP_VERSION)


@router.get("/health/ready", response_model=ReadinessResponse)
async def get_readiness(response: Response) -> ReadinessResponse:
    """Readiness — makes one cheap Supabase query (plan.md §21: "health
    checks cover the API and database"). 503 if the database is
    unreachable; the check itself never raises.
    """
    try:
        get_profile(user_id="00000000-0000-0000-0000-000000000000")
        return ReadinessResponse(status="ok", database="ok")
    except Exception:  # noqa: BLE001 - deliberate: any DB failure means "not ready"
        response.status_code = 503
        return ReadinessResponse(status="error", database="unreachable")
