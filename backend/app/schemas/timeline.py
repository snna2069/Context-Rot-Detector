"""Composed response schema for retrieving a full session timeline.

A message together with its nested tool calls and tool results is enough to
reconstruct the chronological session history, since tool calls always
belong to the message that issued them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.messages import MessageRead
from app.schemas.sessions import AgentSessionRead
from app.schemas.tool_calls import ToolCallRead
from app.schemas.tool_results import ToolResultRead


class ToolCallTimelineEntry(ToolCallRead):
    model_config = ConfigDict(from_attributes=True)

    result: ToolResultRead | None = None


class MessageTimelineEntry(MessageRead):
    model_config = ConfigDict(from_attributes=True)

    tool_calls: list[ToolCallTimelineEntry] = []


class SessionTimelineResponse(BaseModel):
    session: AgentSessionRead
    messages: list[MessageTimelineEntry]
