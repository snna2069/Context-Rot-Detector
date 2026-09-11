from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    AgentSession,
    AnalysisRun,
    AnalysisRunStatus,
    ContextHealthScore,
    ContextSnapshot,
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


def seed_development_data(db: Session) -> AgentSession:
    started_at = datetime.now(UTC) - timedelta(minutes=12)
    session = AgentSession(
        name="Release checklist review",
        status=SessionStatus.COMPLETED,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=12),
        session_metadata={"environment": "development", "source": "seed"},
    )
    db.add(session)
    db.flush()

    user_message = Message(
        session_id=session.id,
        sequence_number=1,
        role=MessageRole.USER,
        content="Review the release checklist and identify blockers.",
        created_at=started_at,
    )
    assistant_message = Message(
        session_id=session.id,
        sequence_number=2,
        role=MessageRole.ASSISTANT,
        content="I will inspect the checklist and verify the deployment status.",
        created_at=started_at + timedelta(minutes=1),
    )
    db.add_all([user_message, assistant_message])
    db.flush()

    tool_call = ToolCall(
        session_id=session.id,
        message_id=assistant_message.id,
        call_index=0,
        tool_name="deployment_status",
        arguments={"environment": "staging"},
        created_at=started_at + timedelta(minutes=2),
    )
    db.add(tool_call)
    db.flush()
    db.add(
        ToolResult(
            session_id=session.id,
            tool_call_id=tool_call.id,
            output={"status": "blocked", "reason": "migration pending"},
            created_at=started_at + timedelta(minutes=3),
        )
    )

    fact = ImportantFact(
        session_id=session.id,
        source_message_id=assistant_message.id,
        subject="staging deployment",
        predicate="status",
        value="blocked",
        confidence=0.98,
        status=FactStatus.VERIFIED,
    )
    db.add(fact)
    db.flush()

    snapshot = ContextSnapshot(
        session_id=session.id,
        sequence_number=3,
        token_count=420,
        content={"included_message_sequences": [1, 2], "fact_ids": [fact.id]},
        created_at=started_at + timedelta(minutes=4),
    )
    db.add(snapshot)

    run = AnalysisRun(
        session_id=session.id,
        analysis_version="foundation-seed-v1",
        status=AnalysisRunStatus.COMPLETED,
        input_sequence_start=1,
        input_sequence_end=3,
        created_at=started_at + timedelta(minutes=5),
        completed_at=started_at + timedelta(minutes=5),
    )
    db.add(run)
    db.flush()

    db.add(
        DetectionEvent(
            session_id=session.id,
            analysis_run_id=run.id,
            detection_type=DetectionType.TOOL_RESULT_MISUSE,
            severity=DetectionSeverity.MEDIUM,
            confidence=0.86,
            explanation="The deployment result reports a pending migration blocker.",
            timestamp=started_at + timedelta(minutes=6),
            related_messages=[assistant_message],
        )
    )
    db.add(
        ContextHealthScore(
            session_id=session.id,
            analysis_run_id=run.id,
            overall_score=0.74,
            relevance_score=0.9,
            consistency_score=0.8,
            instruction_adherence_score=0.85,
            evidence_coverage_score=0.65,
            measured_at=started_at + timedelta(minutes=6),
        )
    )
    db.commit()
    db.refresh(session)
    return session


if __name__ == "__main__":
    with SessionLocal() as session:
        seeded = seed_development_data(session)
        print(f"Seeded development session {seeded.id}")
