from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.schemas.messages import MessageCreate, MessageRead
from app.schemas.sessions import AgentSessionCreate, AgentSessionRead
from app.schemas.timeline import SessionTimelineResponse
from app.schemas.tool_calls import ToolCallCreate, ToolCallRead
from app.schemas.tool_results import ToolResultCreate, ToolResultRead
from app.services import ingestion

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=AgentSessionRead, status_code=201)
def create_session(
    payload: AgentSessionCreate, db: DBSession = Depends(get_db)
) -> AgentSessionRead:
    session = ingestion.create_session(db, payload)
    return AgentSessionRead.model_validate(session)


@router.get("", response_model=list[AgentSessionRead])
def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_db),
) -> list[AgentSessionRead]:
    sessions = ingestion.list_sessions(db, limit=limit, offset=offset)
    return [AgentSessionRead.model_validate(session) for session in sessions]


@router.get("/{session_id}", response_model=AgentSessionRead)
def get_session(session_id: str, db: DBSession = Depends(get_db)) -> AgentSessionRead:
    session = ingestion.get_session(db, session_id)
    return AgentSessionRead.model_validate(session)


@router.post("/{session_id}/messages", response_model=MessageRead, status_code=201)
def add_message(
    session_id: str, payload: MessageCreate, db: DBSession = Depends(get_db)
) -> MessageRead:
    message = ingestion.add_message(db, session_id, payload)
    return MessageRead.model_validate(message)


@router.get("/{session_id}/messages", response_model=list[MessageRead])
def list_messages(
    session_id: str, db: DBSession = Depends(get_db)
) -> list[MessageRead]:
    messages = ingestion.list_messages(db, session_id)
    return [MessageRead.model_validate(message) for message in messages]


@router.post(
    "/{session_id}/messages/{message_id}/tool-calls",
    response_model=ToolCallRead,
    status_code=201,
)
def add_tool_call(
    session_id: str,
    message_id: str,
    payload: ToolCallCreate,
    db: DBSession = Depends(get_db),
) -> ToolCallRead:
    tool_call = ingestion.add_tool_call(db, session_id, message_id, payload)
    return ToolCallRead.model_validate(tool_call)


@router.post(
    "/{session_id}/tool-calls/{tool_call_id}/result",
    response_model=ToolResultRead,
    status_code=201,
)
def add_tool_result(
    session_id: str,
    tool_call_id: str,
    payload: ToolResultCreate,
    db: DBSession = Depends(get_db),
) -> ToolResultRead:
    tool_result = ingestion.add_tool_result(db, session_id, tool_call_id, payload)
    return ToolResultRead.model_validate(tool_result)


@router.get("/{session_id}/timeline", response_model=SessionTimelineResponse)
def get_timeline(
    session_id: str, db: DBSession = Depends(get_db)
) -> SessionTimelineResponse:
    session, messages = ingestion.get_timeline(db, session_id)
    return SessionTimelineResponse(
        session=AgentSessionRead.model_validate(session),
        messages=messages,
    )
