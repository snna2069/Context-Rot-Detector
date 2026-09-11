"""Helpers for building `SessionContext` fixtures directly (no database)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

from app.analysis.context import (
    MessageView,
    SessionContext,
    ToolCallView,
    ToolResultView,
)
from app.models import MessageRole

_id_counter = count(1)


def _next_id(prefix: str) -> str:
    return f"{prefix}-{next(_id_counter)}"


def make_message(
    sequence_number: int,
    role: MessageRole,
    content: str,
    tool_calls: tuple[ToolCallView, ...] = (),
    message_id: str | None = None,
) -> MessageView:
    return MessageView(
        id=message_id or _next_id("msg"),
        sequence_number=sequence_number,
        role=role,
        content=content,
        created_at=datetime(2026, 1, 1, tzinfo=UTC)
        + timedelta(minutes=sequence_number),
        tool_calls=tool_calls,
    )


def make_tool_call(
    message_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    call_index: int = 0,
    result_output: dict[str, Any] | None = None,
    result_is_error: bool = False,
    with_result: bool = True,
) -> ToolCallView:
    tool_call_id = _next_id("tool_call")
    result = None
    if with_result:
        result = ToolResultView(
            id=_next_id("tool_result"),
            tool_call_id=tool_call_id,
            output=result_output or {},
            is_error=result_is_error,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    return ToolCallView(
        id=tool_call_id,
        message_id=message_id,
        call_index=call_index,
        tool_name=tool_name,
        arguments=arguments or {},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        result=result,
    )


def make_context(
    messages: list[MessageView], session_id: str = "session-1"
) -> SessionContext:
    return SessionContext(session_id=session_id, messages=messages)
