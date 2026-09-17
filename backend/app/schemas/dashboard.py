"""Response schema for the Phase 7 dashboard's session list endpoint."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.analysis import ContextHealthScoreRead
from app.schemas.sessions import AgentSessionRead


class SessionOverviewRead(BaseModel):
    session: AgentSessionRead
    message_count: int
    detection_event_count: int
    unsupported_claim_count: int
    latest_health_score: ContextHealthScoreRead | None
