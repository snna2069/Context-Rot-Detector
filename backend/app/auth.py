"""Authentication dependency for the internal single-service deployment."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require the configured internal API key when auth is enabled.

    Development remains usable without credentials by default. Any
    non-development deployment, or an explicit `AUTH_ENABLED=true`, fails
    closed when the key is missing or wrong. `compare_digest` avoids making
    the comparison itself a timing oracle.
    """
    settings = get_settings()
    if not settings.require_api_key:
        return
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is enabled but no API key is configured.",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-API-Key header is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
