from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import campaigns, health, me
from app.schemas import ErrorDetail, ErrorResponse

settings = get_settings()

app = FastAPI(title="Siftora API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        error = ErrorDetail(
            code=str(exc.detail["code"]),
            message=str(exc.detail["message"]),
            details=exc.detail.get("details"),
        )
    else:
        error = ErrorDetail(code="http_error", message=str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code, content=ErrorResponse(error=error).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    error = ErrorDetail(code="validation_error", message="The request could not be validated.")
    return JSONResponse(status_code=422, content=ErrorResponse(error=error).model_dump())


app.include_router(health.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
