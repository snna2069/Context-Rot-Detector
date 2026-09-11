from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import sessions_router
from app.config import get_settings
from app.errors import ConflictError, NotFoundError

settings = get_settings()

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
async def unhandled_exception_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error"},
    )


app.include_router(sessions_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
