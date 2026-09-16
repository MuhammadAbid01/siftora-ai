from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_admin_user
from app.evals.runner import run_all
from app.schemas import EvalReport

router = APIRouter(prefix="/evals", tags=["evals"])


@router.post("/run", response_model=EvalReport)
async def run_evals(
    current_admin: Annotated[CurrentUser, Depends(get_current_admin_user)],
) -> EvalReport:
    """Admin-only (plan.md §7): runs the deterministic eval harness against
    whichever providers are currently configured. Never touches Supabase —
    see specs/phase-5-hardening.md, Non-goals, for why the failure/recovery
    category (which does need the database) isn't exposed here.
    """
    return await run_all()
