from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import ToolResult


def create(db: DBSession, tool_result: ToolResult) -> ToolResult:
    db.add(tool_result)
    db.flush()
    return tool_result


def get_by_tool_call_id(db: DBSession, tool_call_id: str) -> ToolResult | None:
    stmt = select(ToolResult).where(ToolResult.tool_call_id == tool_call_id)
    return db.scalar(stmt)


def list_by_session(db: DBSession, session_id: str) -> list[ToolResult]:
    stmt = select(ToolResult).where(ToolResult.session_id == session_id)
    return list(db.scalars(stmt))
