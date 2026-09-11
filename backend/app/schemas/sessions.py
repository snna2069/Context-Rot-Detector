"""Request/response schemas for creating and reading agent sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import SessionStatus
from app.schemas.common import MAX_METADATA_BYTES, ensure_json_payload_within_limit


class AgentSessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    started_at: datetime | None = None
    session_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value

    @field_validator("session_metadata")
    @classmethod
    def _limit_metadata_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_payload_within_limit(
            value, MAX_METADATA_BYTES, "session_metadata"
        )


class AgentSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime
    session_metadata: dict[str, Any]
