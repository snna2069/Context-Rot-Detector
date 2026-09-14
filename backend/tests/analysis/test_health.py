"""Unit tests for `app.analysis.health.compute_health_score`.

Covers: perfect health with no signals, each dimension being penalized in
isolation, configurable weighting (per-signal penalty and per-dimension
overall weight), and the hallucination-classification-aware multiplier
applied to `UNSUPPORTED_CLAIM` signals.
"""

from __future__ import annotations

from app.analysis.health import HealthScoreWeights, compute_health_score
from app.analysis.signals import Signal
from app.models import DetectionSeverity, DetectionType


def _signal(
    detection_type: DetectionType,
    confidence: float = 0.8,
    metadata: dict | None = None,
) -> Signal:
    return Signal(
        detector_name="test",
        detection_type=detection_type,
        severity=DetectionSeverity.MEDIUM,
        confidence=confidence,
        explanation="test signal",
        metadata=metadata or {},
    )


def test_no_signals_yields_perfect_health_on_every_dimension() -> None:
    result = compute_health_score([])

    assert result.overall_score == 1.0
    assert result.consistency_score == 1.0
    assert result.instruction_adherence_score == 1.0
    assert result.information_retention_score == 1.0
    assert result.relevance_score == 1.0
    assert result.tool_utilization_score == 1.0
    assert result.hallucination_risk_score == 1.0


def test_contradiction_signal_only_penalizes_consistency() -> None:
    result = compute_health_score([_signal(DetectionType.CONTRADICTION)])

    assert result.consistency_score < 1.0
    assert result.instruction_adherence_score == 1.0
    assert result.information_retention_score == 1.0
    assert result.relevance_score == 1.0
    assert result.tool_utilization_score == 1.0
    assert result.hallucination_risk_score == 1.0


def test_fact_loss_and_omission_penalize_information_retention() -> None:
    result = compute_health_score(
        [_signal(DetectionType.FACT_LOSS), _signal(DetectionType.OMISSION)]
    )

    assert result.information_retention_score < 1.0
    # Two contributing signals should penalize more than a single one.
    single = compute_health_score([_signal(DetectionType.FACT_LOSS)])
    assert result.information_retention_score < single.information_retention_score


def test_repetition_and_topic_drift_penalize_relevance() -> None:
    result = compute_health_score([_signal(DetectionType.TOPIC_DRIFT)])
    assert result.relevance_score < 1.0

    result = compute_health_score([_signal(DetectionType.REPETITION)])
    assert result.relevance_score < 1.0


def test_context_growth_and_behavior_shift_never_penalize_any_dimension() -> None:
    result = compute_health_score(
        [_signal(DetectionType.CONTEXT_GROWTH), _signal(DetectionType.BEHAVIOR_SHIFT)]
    )

    assert result.overall_score == 1.0


def test_hallucination_classification_scales_the_penalty() -> None:
    unsupported = compute_health_score(
        [
            _signal(
                DetectionType.UNSUPPORTED_CLAIM,
                confidence=0.8,
                metadata={"classification": "unsupported"},
            )
        ]
    )
    high_confidence = compute_health_score(
        [
            _signal(
                DetectionType.UNSUPPORTED_CLAIM,
                confidence=0.8,
                metadata={"classification": "high_confidence_hallucination"},
            )
        ]
    )

    assert (
        high_confidence.hallucination_risk_score < unsupported.hallucination_risk_score
    )
    # Only the hallucination_risk dimension is affected.
    assert high_confidence.consistency_score == 1.0


def test_unknown_classification_falls_back_to_least_severe_multiplier() -> None:
    unknown = compute_health_score(
        [
            _signal(
                DetectionType.UNSUPPORTED_CLAIM,
                confidence=0.8,
                metadata={"classification": "something_new"},
            )
        ]
    )
    unsupported = compute_health_score(
        [
            _signal(
                DetectionType.UNSUPPORTED_CLAIM,
                confidence=0.8,
                metadata={"classification": "unsupported"},
            )
        ]
    )

    assert unknown.hallucination_risk_score == unsupported.hallucination_risk_score


def test_overall_score_respects_configurable_penalty_per_signal() -> None:
    signals = [_signal(DetectionType.CONTRADICTION)]

    lenient = compute_health_score(signals, HealthScoreWeights(penalty_per_signal=0.01))
    harsh = compute_health_score(signals, HealthScoreWeights(penalty_per_signal=0.5))

    assert lenient.consistency_score > harsh.consistency_score


def test_overall_score_respects_configurable_dimension_weights() -> None:
    signals = [_signal(DetectionType.CONTRADICTION)]

    # Weight consistency at zero: it should still be reported, but must
    # not affect the overall score at all.
    weights = HealthScoreWeights(
        dimension_weights={
            "consistency": 0.0,
            "instruction_adherence": 1.0,
            "information_retention": 1.0,
            "relevance": 1.0,
            "tool_utilization": 1.0,
            "hallucination_risk": 1.0,
        }
    )
    result = compute_health_score(signals, weights)

    assert result.consistency_score < 1.0
    assert result.overall_score == 1.0


def test_from_settings_builds_weights_from_configured_values() -> None:
    from app.config import Settings

    settings = Settings(
        health_penalty_per_signal=0.3,
        health_weight_consistency=2.0,
        health_weight_instruction_adherence=1.0,
        health_weight_information_retention=1.0,
        health_weight_relevance=1.0,
        health_weight_tool_utilization=1.0,
        health_weight_hallucination_risk=1.0,
    )

    weights = HealthScoreWeights.from_settings(settings)

    assert weights.penalty_per_signal == 0.3
    assert weights.dimension_weights["consistency"] == 2.0
