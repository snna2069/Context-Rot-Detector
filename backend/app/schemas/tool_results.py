"""Request/response schemas for tool results."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import MAX_TOOL_OUTPUT_BYTES, ensure_json_payload_within_limit


class ToolResultCreate(BaseModel):
    output: dict[str, Any] = Field(default_factory=dict)
    is_error: bool = False
    created_at: datetime | None = None

    @field_validator("output")
    @classmethod
    def _limit_output_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_payload_within_limit(value, MAX_TOOL_OUTPUT_BYTES, "output")


class ToolResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    tool_call_id: str
    output: dict[str, Any]
    is_error: bool
    created_at: datetime
