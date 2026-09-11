"""Request/response schemas for messages.

`sequence_number` and `provider_message_id` are both optional: a
provider-agnostic caller can either let the server assign the next sequence
number, or supply its own ordering plus an idempotency key so replays of the
same upstream event are rejected as duplicates rather than stored twice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import MessageRole
from app.schemas.common import (
    MAX_METADATA_BYTES,
    MAX_TEXT_CONTENT_LENGTH,
    ensure_json_payload_within_limit,
)


class MessageCreate(BaseModel):
    role: MessageRole
    content: str = Field(min_length=1, max_length=MAX_TEXT_CONTENT_LENGTH)
    sequence_number: int | None = Field(default=None, ge=1)
    created_at: datetime | None = None
    provider_message_id: str | None = Field(default=None, max_length=255)
    message_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def _reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value

    @field_validator("provider_message_id")
    @classmethod
    def _reject_blank_provider_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("provider_message_id must not be blank when provided")
        return value

    @field_validator("message_metadata")
    @classmethod
    def _limit_metadata_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_payload_within_limit(
            value, MAX_METADATA_BYTES, "message_metadata"
        )


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    sequence_number: int
    role: MessageRole
    content: str
    created_at: datetime
    provider_message_id: str | None
    message_metadata: dict[str, Any]
