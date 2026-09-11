from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import AgentSession


def create(
    db: DBSession, *, name: str, started_at: datetime, session_metadata: dict[str, Any]
) -> AgentSession:
    session = AgentSession(
        name=name, started_at=started_at, session_metadata=session_metadata
    )
    db.add(session)
    db.flush()
    return session


def get_by_id(db: DBSession, session_id: str) -> AgentSession | None:
    return db.get(AgentSession, session_id)


def list_all(db: DBSession, *, limit: int = 50, offset: int = 0) -> list[AgentSession]:
    stmt = (
        select(AgentSession)
        .order_by(AgentSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))
