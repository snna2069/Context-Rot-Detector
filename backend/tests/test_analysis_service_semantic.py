"""End-to-end (service-layer) test verifying that `run_analysis` wires an
injected semantic provider alongside the deterministic detectors, and
that the resulting semantic `DetectionEvent` is actually persisted --
not just computed in memory."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, DetectionType, MessageRole
from app.schemas.messages import MessageCreate
from app.schemas.sessions import AgentSessionCreate
from app.schemas.tool_calls import ToolCallCreate
from app.schemas.tool_results import ToolResultCreate
from app.services import analysis as analysis_service
from app.services import ingestion
from app.services.llm.types import (
    ClaimSupportResult,
    EvidenceClassification,
    ExtractedFact,
    ImportantFactsResult,
    RelevanceResult,
)
from tests.llm.fake_provider import ScriptedAnalysisProvider, result


@pytest.fixture
def db() -> Generator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = session_local()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_run_analysis_persists_semantic_detection_event(db: Session) -> None:
    session = ingestion.create_session(db, AgentSessionCreate(name="semantic-test"))
    task = "What is the capital of France?"
    reply = "Here is a chocolate cake recipe."
    ingestion.add_message(
        db, session.id, MessageCreate(role=MessageRole.USER, content=task)
    )
    ingestion.add_message(
        db, session.id, MessageCreate(role=MessageRole.ASSISTANT, content=reply)
    )

    provider = ScriptedAnalysisProvider(
        relevance_by_pair={
            (task, reply): RelevanceResult(is_relevant=False, **result(0.9)),
        },
    )

    run = analysis_service.run_analysis(db, session.id, provider=provider)

    assert run.status == "completed"
    events = analysis_service.list_detection_events(db, session.id)
    topic_drift_events = [
        e for e in events if e.detection_type == DetectionType.TOPIC_DRIFT
    ]
    assert len(topic_drift_events) == 1
    assert topic_drift_events[0].confidence == 0.9


def test_run_analysis_defaults_to_unavailable_provider_without_error(
    db: Session,
) -> None:
    """No explicit provider given -- must fall back to
    `get_analysis_provider()` (Unavailable in tests, no LLM_API_KEY set)
    without raising, and produce no semantic-only signals."""
    session = ingestion.create_session(db, AgentSessionCreate(name="default-provider"))
    ingestion.add_message(
        db, session.id, MessageCreate(role=MessageRole.USER, content="Hello!")
    )
    ingestion.add_message(
        db,
        session.id,
        MessageCreate(role=MessageRole.ASSISTANT, content="Hi, how can I help?"),
    )

    run = analysis_service.run_analysis(db, session.id)

    assert run.status == "completed"


def test_run_analysis_persists_hallucination_classification_metadata(
    db: Session,
) -> None:
    """The evidence-based classification behind an `UNSUPPORTED_CLAIM`
    signal must survive a full round trip through the database -- not
    just exist transiently on the in-memory `Signal` -- since the
    dashboard's hallucination-analysis view reads it back from stored
    `DetectionEvent` rows, never recomputes it."""
    session = ingestion.create_session(db, AgentSessionCreate(name="hallucination-md"))
    claim = "The server has 99.999% uptime this month."
    ingestion.add_message(
        db, session.id, MessageCreate(role=MessageRole.ASSISTANT, content="checking")
    )
    tool_message = ingestion.list_messages(db, session.id)[0]
    tool_call = ingestion.add_tool_call(
        db,
        session.id,
        tool_message.id,
        ToolCallCreate(tool_name="get_uptime", arguments={}),
    )
    ingestion.add_tool_result(
        db,
        session.id,
        tool_call.id,
        ToolResultCreate(output={"uptime_percent": 97.2}),
    )
    ingestion.add_message(
        db, session.id, MessageCreate(role=MessageRole.ASSISTANT, content=claim)
    )

    provider = ScriptedAnalysisProvider(
        facts_by_text={
            claim: ImportantFactsResult(
                facts=(ExtractedFact(text="server has 99.999% uptime this month"),),
                **result(0.9),
            )
        },
        claim_support_by_claim={
            "server has 99.999% uptime this month": ClaimSupportResult(
                classification=EvidenceClassification.UNSUPPORTED,
                **result(0.8),
            ),
        },
    )

    analysis_service.run_analysis(db, session.id, provider=provider)

    events = analysis_service.list_detection_events(db, session.id)
    unsupported_events = [
        e for e in events if e.detection_type == DetectionType.UNSUPPORTED_CLAIM
    ]
    assert len(unsupported_events) == 1
    assert unsupported_events[0].event_metadata["classification"] == (
        "possible_hallucination"
    )
