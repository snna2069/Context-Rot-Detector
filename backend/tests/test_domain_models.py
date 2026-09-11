from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    AgentSession,
    AnalysisRun,
    AnalysisRunStatus,
    Base,
    ContextHealthScore,
    DetectionEvent,
    DetectionSeverity,
    DetectionType,
    FactStatus,
    ImportantFact,
    Message,
    MessageRole,
    SessionStatus,
    ToolCall,
    ToolResult,
)
from app.seed import seed_development_data


def test_domain_relationships_persist_and_round_trip() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        session = AgentSession(
            name="Test session",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(UTC),
        )
        db.add(session)
        db.flush()

        message = Message(
            session_id=session.id,
            sequence_number=1,
            role=MessageRole.ASSISTANT,
            content="Checking deployment.",
        )
        db.add(message)
        db.flush()

        call = ToolCall(
            session_id=session.id,
            message_id=message.id,
            call_index=0,
            tool_name="status",
            arguments={"environment": "staging"},
        )
        db.add(call)
        db.flush()
        db.add(
            ToolResult(
                session_id=session.id,
                tool_call_id=call.id,
                output={"status": "ok"},
            )
        )

        fact = ImportantFact(
            session_id=session.id,
            source_message_id=message.id,
            subject="deployment",
            predicate="status",
            value="ready",
            confidence=0.9,
            status=FactStatus.VERIFIED,
        )
        db.add(fact)
        db.flush()

        run = AnalysisRun(
            session_id=session.id,
            analysis_version="test-v1",
            status=AnalysisRunStatus.COMPLETED,
        )
        db.add(run)
        db.flush()
        detection = DetectionEvent(
            session_id=session.id,
            analysis_run_id=run.id,
            detection_type=DetectionType.CONTRADICTION,
            severity=DetectionSeverity.LOW,
            confidence=0.7,
            explanation="Test evidence",
            related_messages=[message],
        )
        db.add(detection)
        db.add(
            ContextHealthScore(
                session_id=session.id,
                analysis_run_id=run.id,
                overall_score=0.8,
            )
        )
        db.commit()

        loaded = db.scalar(select(AgentSession).where(AgentSession.id == session.id))
        assert loaded is not None
        assert loaded.messages[0].tool_calls[0].result.output == {"status": "ok"}
        assert (
            loaded.important_facts[0].source_message.content == "Checking deployment."
        )
        assert loaded.detection_events[0].related_messages[0].id == message.id
        assert loaded.health_scores[0].overall_score == 0.8


def test_message_sequence_is_unique_per_session() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        session = AgentSession(
            name="Duplicate sequence",
            started_at=datetime.now(UTC),
        )
        db.add(session)
        db.flush()
        db.add_all(
            [
                Message(
                    session_id=session.id,
                    sequence_number=1,
                    role=MessageRole.USER,
                    content="first",
                ),
                Message(
                    session_id=session.id,
                    sequence_number=1,
                    role=MessageRole.ASSISTANT,
                    content="duplicate",
                ),
            ]
        )

        try:
            db.commit()
        except Exception:
            db.rollback()
        else:
            raise AssertionError("Duplicate message sequence should be rejected")


def test_development_seed_creates_a_realistic_session() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        session = seed_development_data(db)

        assert session.name == "Release checklist review"
        assert len(session.messages) == 2
        assert len(session.tool_calls) == 1
        assert session.tool_results[0].output["status"] == "blocked"
        assert session.important_facts[0].status == FactStatus.VERIFIED
        assert (
            session.detection_events[0].detection_type
            == DetectionType.TOOL_RESULT_MISUSE
        )
        assert session.health_scores[0].overall_score == 0.74
