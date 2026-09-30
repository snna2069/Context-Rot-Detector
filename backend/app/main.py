import logging

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import analysis_router, dashboard_router, sessions_router
from app.config import get_settings
from app.database import get_db
from app.errors import ConflictError, NotFoundError

settings = get_settings()

# Configure logging once, at the application entry point. Without this
# the stdlib root logger drops anything below WARNING, which previously
# meant detector failures logged by `app.analysis.engine` were invisible.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# Reject clearly oversized request bodies before they are parsed/validated.
# This is a transport-level backstop; individual fields also enforce their
# own, tighter size limits in the Pydantic schemas.
MAX_REQUEST_BODY_BYTES = 2_000_000

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "payload_too_large"},
        )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "details": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(
    _request: Request, exc: NotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "detail": str(exc)},
    )


@app.exception_handler(ConflictError)
async def conflict_exception_handler(
    _request: Request, exc: ConflictError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "conflict", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log with the traceback before returning the opaque 500. Previously
    # the exception was discarded entirely, so production failures left
    # no trace anywhere.
    logger.exception(
        "Unhandled exception while handling %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error"},
    )


app.include_router(sessions_router)
app.include_router(analysis_router)
app.include_router(dashboard_router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Liveness + database readiness.

    A static "ok" would report healthy during a total database outage,
    which makes the check useless for deciding whether this instance can
    actually serve traffic. Takes the database session via the normal
    `get_db` dependency so it exercises the same connection path as real
    requests (and so tests can override it).
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unreachable",
                "detail": type(exc).__name__,
            },
        )
    return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
