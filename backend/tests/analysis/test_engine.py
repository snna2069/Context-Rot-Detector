from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.engine import AnalysisEngine
from app.analysis.signals import Signal
from app.models import DetectionSeverity, DetectionType, MessageRole
from tests.analysis.helpers import make_context, make_message


def test_engine_aggregates_signals_and_computes_health_score() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The deadline is March 15th."),
        make_message(2, MessageRole.ASSISTANT, "The deadline is next Tuesday."),
    ]
    context = make_context(messages)

    result = AnalysisEngine().run(context)

    assert any(s.detection_type == DetectionType.CONTRADICTION for s in result.signals)
    assert 0.0 <= result.health_score.overall_score <= 1.0
    assert result.health_score.consistency_score < 1.0


def test_engine_returns_perfect_health_for_uneventful_session() -> None:
    messages = [
        make_message(1, MessageRole.USER, "Hello there."),
        make_message(2, MessageRole.ASSISTANT, "Hi! How can I help you today?"),
    ]
    context = make_context(messages)

    result = AnalysisEngine().run(context)

    assert result.health_score.overall_score == 1.0


class _ExplodingDetector:
    name = "exploding"

    def detect(self, context: SessionContext) -> list[Signal]:
        raise RuntimeError("boom")


class _WellBehavedDetector:
    name = "well_behaved"

    def detect(self, context: SessionContext) -> list[Signal]:
        return [
            Signal(
                detector_name=self.name,
                detection_type=DetectionType.CONTEXT_GROWTH,
                severity=DetectionSeverity.INFO,
                confidence=0.5,
                explanation="test signal",
            )
        ]


def test_engine_is_resilient_to_a_failing_detector() -> None:
    context = make_context(
        [make_message(1, MessageRole.USER, "hello")], session_id="session-x"
    )
    engine = AnalysisEngine(detectors=[_ExplodingDetector(), _WellBehavedDetector()])

    result = engine.run(context)

    assert len(result.signals) == 1
    assert result.signals[0].detector_name == "well_behaved"
