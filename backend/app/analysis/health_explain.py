"""Turning a change in context-health score into plain-language reasons.

Produces bullets like the ones in the Phase 6 brief:

    Context health decreased because:
    - contradiction rate increased
    - previously established facts were ignored
    - irrelevant context increased
    - unsupported claims increased

Each reason is derived from a concrete, countable change in detection
events between two analysis runs -- never invented or LLM-generated --
so the explanation is always traceable back to specific signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models import DetectionType

ScoreDirection = Literal["increased", "decreased", "unchanged", "initial"]

# Ordered so the resulting bullet list reads in a sensible priority: the
# strongest safety-relevant concerns (contradictions, hallucination risk)
# first, then adherence/retention/relevance issues.
_EXPLANATION_RULES: tuple[tuple[str, frozenset[DetectionType]], ...] = (
    ("the contradiction rate increased", frozenset({DetectionType.CONTRADICTION})),
    (
        "unsupported or possibly-hallucinated claims increased",
        frozenset({DetectionType.UNSUPPORTED_CLAIM}),
    ),
    (
        "previously established facts were ignored or lost",
        frozenset({DetectionType.FACT_LOSS, DetectionType.OMISSION}),
    ),
    (
        "the assistant drifted from its given instructions more often",
        frozenset({DetectionType.INSTRUCTION_DRIFT}),
    ),
    (
        "irrelevant or repeated context increased",
        frozenset({DetectionType.TOPIC_DRIFT, DetectionType.REPETITION}),
    ),
    (
        "tool results were used less effectively",
        frozenset({DetectionType.TOOL_RESULT_MISUSE}),
    ),
)

_SCORE_CHANGE_EPSILON = 0.005


@dataclass(frozen=True)
class HealthChangeExplanation:
    direction: ScoreDirection
    score_delta: float | None
    reasons: tuple[str, ...]
    headline: str


def _count_by_type(
    detection_types: list[DetectionType],
) -> dict[DetectionType, int]:
    counts: dict[DetectionType, int] = {}
    for detection_type in detection_types:
        counts[detection_type] = counts.get(detection_type, 0) + 1
    return counts


def explain_health_change(
    current_overall_score: float,
    current_detection_types: list[DetectionType],
    previous_overall_score: float | None = None,
    previous_detection_types: list[DetectionType] | None = None,
) -> HealthChangeExplanation:
    """Explain the change from one analysis run's signals to the next.

    Pass `previous_overall_score=None` for the first analysis run of a
    session -- there is nothing to compare against yet, so `direction`
    is `"initial"` and no reasons are produced.
    """
    current_counts = _count_by_type(current_detection_types)

    if previous_overall_score is None:
        return HealthChangeExplanation(
            direction="initial",
            score_delta=None,
            reasons=(),
            headline="This is the first recorded health score for this session.",
        )

    previous_counts = _count_by_type(previous_detection_types or [])
    delta = round(current_overall_score - previous_overall_score, 3)

    if delta <= -_SCORE_CHANGE_EPSILON:
        direction: ScoreDirection = "decreased"
    elif delta >= _SCORE_CHANGE_EPSILON:
        direction = "increased"
    else:
        direction = "unchanged"

    reasons = tuple(
        label
        for label, types in _EXPLANATION_RULES
        if sum(current_counts.get(t, 0) for t in types)
        > sum(previous_counts.get(t, 0) for t in types)
    )

    if direction == "decreased":
        headline = "Context health decreased because:"
    elif direction == "increased":
        headline = "Context health improved because fewer issues were detected:"
    else:
        headline = "Context health stayed roughly the same since the last run."

    return HealthChangeExplanation(
        direction=direction,
        score_delta=delta,
        reasons=reasons,
        headline=headline,
    )
