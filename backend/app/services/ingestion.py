"""Business rules for ingesting agent session events.

This module is the only place that enforces ordering, deduplication, and
existence checks for ingestion. API routes call these functions and never
touch repositories or the ORM session directly, and repositories never
enforce business rules -- they only read/write rows. This keeps the rules
in one place, provider-agnostic, and independently testable.
"""

from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.errors import (
    DuplicateMessageError,
    DuplicateToolCallIndexError,
    DuplicateToolResultError,
    InvalidMessageSequenceError,
    MessageNotFoundError,
    SessionNotFoundError,
    ToolCallNotFoundError,
)
from app.models import AgentSession, Message, ToolCall, ToolResult, utc_now
from app.repositories import messages as messages_repo
from app.repositories import sessions as sessions_repo
from app.repositories import tool_calls as tool_calls_repo
from app.repositories import tool_results as tool_results_repo
from app.schemas.messages import MessageCreate
from app.schemas.sessions import AgentSessionCreate
from app.schemas.tool_calls import ToolCallCreate
from app.schemas.tool_results import ToolResultCreate


def create_session(db: DBSession, payload: AgentSessionCreate) -> AgentSession:
    session = sessions_repo.create(
        db,
        name=payload.name,
        started_at=payload.started_at or utc_now(),
        session_metadata=payload.session_metadata,
    )
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_id: str) -> AgentSession:
    session = sessions_repo.get_by_id(db, session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    return session


def list_sessions(
    db: DBSession, *, limit: int = 50, offset: int = 0
) -> list[AgentSession]:
    return sessions_repo.list_all(db, limit=limit, offset=offset)


def add_message(db: DBSession, session_id: str, payload: MessageCreate) -> Message:
    get_session(db, session_id)

    if payload.provider_message_id is not None:
        existing = messages_repo.get_by_provider_message_id(
            db, session_id, payload.provider_message_id
        )
        if existing is not None:
            raise DuplicateMessageError(payload.provider_message_id)

    last_sequence = messages_repo.get_last_sequence_number(db, session_id)
    if payload.sequence_number is None:
        sequence_number = last_sequence + 1
    elif payload.sequence_number > last_sequence:
        sequence_number = payload.sequence_number
    else:
        raise InvalidMessageSequenceError(
            session_id, payload.sequence_number, last_sequence
        )

    message = Message(
        session_id=session_id,
        sequence_number=sequence_number,
        role=payload.role,
        content=payload.content,
        created_at=payload.created_at or utc_now(),
        provider_message_id=payload.provider_message_id,
        message_metadata=payload.message_metadata,
    )
    messages_repo.create(db, message)
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: DBSession, session_id: str) -> list[Message]:
    get_session(db, session_id)
    return messages_repo.list_by_session(db, session_id)


def add_tool_call(
    db: DBSession, session_id: str, message_id: str, payload: ToolCallCreate
) -> ToolCall:
    get_session(db, session_id)
    message = messages_repo.get_by_id(db, message_id)
    if message is None or message.session_id != session_id:
        raise MessageNotFoundError(message_id)

    if payload.call_index is None:
        call_index = tool_calls_repo.get_next_call_index(db, message_id)
    else:
        existing = tool_calls_repo.get_by_message_and_index(
            db, message_id, payload.call_index
        )
        if existing is not None:
            raise DuplicateToolCallIndexError(message_id, payload.call_index)
        call_index = payload.call_index

    tool_call = ToolCall(
        session_id=session_id,
        message_id=message_id,
        call_index=call_index,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
        created_at=payload.created_at or utc_now(),
    )
    tool_calls_repo.create(db, tool_call)
    db.commit()
    db.refresh(tool_call)
    return tool_call


def add_tool_result(
    db: DBSession, session_id: str, tool_call_id: str, payload: ToolResultCreate
) -> ToolResult:
    get_session(db, session_id)
    tool_call = tool_calls_repo.get_by_id(db, tool_call_id)
    if tool_call is None or tool_call.session_id != session_id:
        raise ToolCallNotFoundError(tool_call_id)

    existing = tool_results_repo.get_by_tool_call_id(db, tool_call_id)
    if existing is not None:
        raise DuplicateToolResultError(tool_call_id)

    tool_result = ToolResult(
        session_id=session_id,
        tool_call_id=tool_call_id,
        output=payload.output,
        is_error=payload.is_error,
        created_at=payload.created_at or utc_now(),
    )
    tool_results_repo.create(db, tool_result)
    db.commit()
    db.refresh(tool_result)
    return tool_result


def get_timeline(db: DBSession, session_id: str) -> tuple[AgentSession, list[Message]]:
    session = get_session(db, session_id)
    messages = messages_repo.list_by_session(db, session_id)
    return session, messages
