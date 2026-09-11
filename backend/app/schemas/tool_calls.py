"""Request/response schemas for tool calls."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import (
    MAX_TOOL_ARGUMENTS_BYTES,
    ensure_json_payload_within_limit,
)


class ToolCallCreate(BaseModel):
    tool_name: str = Field(min_length=1, max_length=200)
    call_index: int | None = Field(default=None, ge=0)
    arguments: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @field_validator("tool_name")
    @classmethod
    def _reject_blank_tool_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool_name must not be blank")
        return value

    @field_validator("arguments")
    @classmethod
    def _limit_arguments_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_payload_within_limit(
            value, MAX_TOOL_ARGUMENTS_BYTES, "arguments"
        )


class ToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    message_id: str
    call_index: int
    tool_name: str
    arguments: dict[str, Any]
    created_at: datetime
