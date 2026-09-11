from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models import ToolCall


def create(db: DBSession, tool_call: ToolCall) -> ToolCall:
    db.add(tool_call)
    db.flush()
    return tool_call


def get_by_id(db: DBSession, tool_call_id: str) -> ToolCall | None:
    return db.get(ToolCall, tool_call_id)


def get_by_message_and_index(
    db: DBSession, message_id: str, call_index: int
) -> ToolCall | None:
    stmt = select(ToolCall).where(
        ToolCall.message_id == message_id, ToolCall.call_index == call_index
    )
    return db.scalar(stmt)


def get_next_call_index(db: DBSession, message_id: str) -> int:
    stmt = select(func.max(ToolCall.call_index)).where(
        ToolCall.message_id == message_id
    )
    highest = db.scalar(stmt)
    return 0 if highest is None else highest + 1


def list_by_session(db: DBSession, session_id: str) -> list[ToolCall]:
    stmt = (
        select(ToolCall)
        .where(ToolCall.session_id == session_id)
        .order_by(ToolCall.call_index)
    )
    return list(db.scalars(stmt))
