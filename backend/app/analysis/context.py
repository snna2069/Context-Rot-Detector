"""Plain-data session view used as the sole input to all detectors.

Detectors never touch the ORM/SQLAlchemy session directly. This keeps them
independently testable (a test can build a `SessionContext` by hand with no
database) and reusable outside of the current transport (API today, maybe
a batch job or CLI later).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models import MessageRole


@dataclass(frozen=True)
class ToolResultView:
    id: str
    tool_call_id: str
    output: dict[str, Any]
    is_error: bool
    created_at: datetime


@dataclass(frozen=True)
class ToolCallView:
    id: str
    message_id: str
    call_index: int
    tool_name: str
    arguments: dict[str, Any]
    created_at: datetime
    result: ToolResultView | None = None


@dataclass(frozen=True)
class MessageView:
    id: str
    sequence_number: int
    role: MessageRole
    content: str
    created_at: datetime
    provider_message_id: str | None = None
    tool_calls: tuple[ToolCallView, ...] = ()


@dataclass
class SessionContext:
    """Everything a detector is allowed to look at for one session."""

    session_id: str
    messages: list[MessageView] = field(default_factory=list)

    def messages_by_role(self, role: MessageRole) -> list[MessageView]:
        return [m for m in self.messages if m.role == role]

    def all_tool_calls(self) -> list[ToolCallView]:
        return [tc for m in self.messages for tc in m.tool_calls]


def build_session_context(
    session_id: str,
    messages: list[Any],
    tool_calls: list[Any],
    tool_results: list[Any],
) -> SessionContext:
    """Build a `SessionContext` from ORM rows (or any duck-typed equivalent).

    Accepts anything with matching attributes rather than the concrete
    SQLAlchemy models, so tests can pass simple namespace-like objects too.
    """
    results_by_tool_call_id = {tr.tool_call_id: tr for tr in tool_results}

    tool_call_views_by_message: dict[str, list[ToolCallView]] = {}
    for tc in tool_calls:
        result = results_by_tool_call_id.get(tc.id)
        result_view = (
            ToolResultView(
                id=result.id,
                tool_call_id=result.tool_call_id,
                output=result.output,
                is_error=result.is_error,
                created_at=result.created_at,
            )
            if result is not None
            else None
        )
        view = ToolCallView(
            id=tc.id,
            message_id=tc.message_id,
            call_index=tc.call_index,
            tool_name=tc.tool_name,
            arguments=tc.arguments,
            created_at=tc.created_at,
            result=result_view,
        )
        tool_call_views_by_message.setdefault(tc.message_id, []).append(view)

    for call_views in tool_call_views_by_message.values():
        call_views.sort(key=lambda v: v.call_index)

    message_views = [
        MessageView(
            id=m.id,
            sequence_number=m.sequence_number,
            role=MessageRole(m.role),
            content=m.content,
            created_at=m.created_at,
            provider_message_id=m.provider_message_id,
            tool_calls=tuple(tool_call_views_by_message.get(m.id, [])),
        )
        for m in sorted(messages, key=lambda m: m.sequence_number)
    ]
    return SessionContext(session_id=session_id, messages=message_views)
