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


def list_by_session(db: DBSession, session_id: str) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_number)
    )
    return list(db.scalars(stmt))
