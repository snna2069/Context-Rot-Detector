from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models import Message


def create(db: DBSession, message: Message) -> Message:
    db.add(message)
    db.flush()
    return message


def get_by_id(db: DBSession, message_id: str) -> Message | None:
    return db.get(Message, message_id)


def get_by_provider_message_id(
    db: DBSession, session_id: str, provider_message_id: str
) -> Message | None:
    stmt = select(Message).where(
        Message.session_id == session_id,
        Message.provider_message_id == provider_message_id,
    )
    return db.scalar(stmt)


def get_last_sequence_number(db: DBSession, session_id: str) -> int:
    stmt = select(func.max(Message.sequence_number)).where(
        Message.session_id == session_id
    )
    return db.scalar(stmt) or 0


def list_by_session(
    db: DBSession, session_id: str, *, limit: int | None = None, offset: int = 0
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_number)
    )
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def count_by_session(db: DBSession, session_id: str) -> int:
    stmt = select(func.count(Message.id)).where(Message.session_id == session_id)
    return db.scalar(stmt) or 0


def count_after_sequence(db: DBSession, session_id: str, sequence_number: int) -> int:
    """Messages ingested after a given sequence number.

    Used to decide whether stored analysis results still cover the whole
    session.
    """
    stmt = select(func.count(Message.id)).where(
        Message.session_id == session_id,
        Message.sequence_number > sequence_number,
    )
    return db.scalar(stmt) or 0


def count_by_sessions(db: DBSession, session_ids: list[str]) -> dict[str, int]:
    """Message count per session, in one query instead of one-per-session.

    Used by the dashboard's session list, which needs a lightweight
    per-session summary for a whole page of sessions at once.
    """
    if not session_ids:
        return {}
    stmt = (
        select(Message.session_id, func.count(Message.id))
        .where(Message.session_id.in_(session_ids))
        .group_by(Message.session_id)
    )
    return dict(db.execute(stmt).all())
