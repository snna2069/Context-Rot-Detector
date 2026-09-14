"""Unit tests for `app.analysis.health_explain.explain_health_change`."""

from __future__ import annotations

from app.analysis.health_explain import explain_health_change
from app.models import DetectionType


def test_first_run_is_reported_as_initial_with_no_reasons() -> None:
    result = explain_health_change(
        current_overall_score=0.9,
        current_detection_types=[DetectionType.CONTRADICTION],
        previous_overall_score=None,
    )

    assert result.direction == "initial"
    assert result.reasons == ()
    assert result.score_delta is None


def test_decreased_score_lists_reasons_for_each_increased_category() -> None:
    result = explain_health_change(
        current_overall_score=0.6,
        current_detection_types=[
            DetectionType.CONTRADICTION,
            DetectionType.CONTRADICTION,
            DetectionType.UNSUPPORTED_CLAIM,
            DetectionType.FACT_LOSS,
        ],
        previous_overall_score=0.9,
        previous_detection_types=[DetectionType.CONTRADICTION],
    )

    assert result.direction == "decreased"
    assert result.score_delta == -0.3
    assert "the contradiction rate increased" in result.reasons
    assert "unsupported or possibly-hallucinated claims increased" in result.reasons
    assert "previously established facts were ignored or lost" in result.reasons
    assert result.headline == "Context health decreased because:"


def test_stable_score_with_no_new_signals_lists_no_reasons() -> None:
    result = explain_health_change(
        current_overall_score=0.9,
        current_detection_types=[DetectionType.CONTRADICTION],
        previous_overall_score=0.9,
        previous_detection_types=[DetectionType.CONTRADICTION],
    )

    assert result.direction == "unchanged"
    assert result.reasons == ()


def test_improved_score_reports_increased_direction() -> None:
    result = explain_health_change(
        current_overall_score=0.95,
        current_detection_types=[],
        previous_overall_score=0.6,
        previous_detection_types=[DetectionType.CONTRADICTION, DetectionType.OMISSION],
    )

    assert result.direction == "increased"
    assert result.reasons == ()
    assert "improved" in result.headline


def test_only_categories_that_actually_increased_are_reported() -> None:
    result = explain_health_change(
        current_overall_score=0.7,
        current_detection_types=[
            DetectionType.CONTRADICTION,
            DetectionType.TOPIC_DRIFT,
        ],
        previous_overall_score=0.8,
        previous_detection_types=[
            DetectionType.CONTRADICTION,
            DetectionType.CONTRADICTION,
        ],
    )

    # Contradiction count went down (2 -> 1); topic drift went up (0 -> 1).
    assert "the contradiction rate increased" not in result.reasons
    assert "irrelevant or repeated context increased" in result.reasons
