"""Composite context-health scoring.

Turns the raw list of `Signal`s produced by the detectors into the
sub-scores tracked by `ContextHealthScore` plus a weighted overall score,
so health can be trended over time per session (one row per analysis
run). See `app.analysis.health_trend` for trending across runs and
`app.analysis.health_explain` for turning a score change into a plain-
language explanation.

IMPORTANT -- this is a prototype engineering metric, not a scientifically
validated measurement. It summarizes what the detectors themselves found
in this run; it is not calibrated against any external ground truth of
"true" context quality, and the weights/penalties below are reasoned
defaults, not the result of empirical tuning against labeled data. Treat
trends and relative comparisons within one session as more meaningful
than the absolute number.

Design notes
-----------------
- Every sub-score is in [0, 1], where 1.0 means "no evidence of a problem
  in this dimension" and 0.0 means "maximum observed evidence of a
  problem." These are deliberately *relative* scores derived from the
  signals actually raised in this run, not calibrated against any
  external ground truth -- they are a summary of the detectors' own
  findings, not an independent judgment.
- `CONTEXT_GROWTH` and `BEHAVIOR_SHIFT` signals are informational trend
  signals and are intentionally excluded from the penalty-based
  sub-scores below; they are surfaced as detection events but do not by
  themselves reduce the health score, per the instruction to never treat
  length/growth alone as rot.
- Six dimensions are tracked (rather than one flat number) so a
  degrading score is explainable: which specific detector families are
  driving it. `REPETITION` is folded into `relevance` (repeated content
  is a form of irrelevant/low-information context) and `FACT_LOSS`/
  `OMISSION` are folded into `information_retention` (both describe
  previously available information failing to carry forward), which
  keeps the schema and weighting configuration small while still
  covering every dimension named in the Phase 6 brief. "Contradiction
  frequency" is captured implicitly: each additional contradiction
  signal adds another penalty term, so a session with more contradictions
  scores lower than one with a single isolated one, without needing a
  separate "frequency" column.
- Weights are configurable (`HealthScoreWeights`), not hard-coded at each
  call site, so the relative importance of a dimension -- or how harshly
  an individual signal is penalized -- can be tuned via environment
  configuration (see `app.config.Settings`) without touching detector or
  scoring code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.analysis.signals import Signal
from app.models import DetectionType

if TYPE_CHECKING:
    from app.config import Settings

# Detection types that reduce each sub-score. A signal of a type not
# listed here (currently only CONTEXT_GROWTH and BEHAVIOR_SHIFT) is
# informational and never penalizes any sub-score.
_CONSISTENCY_TYPES = {DetectionType.CONTRADICTION}
_INSTRUCTION_ADHERENCE_TYPES = {DetectionType.INSTRUCTION_DRIFT}
_INFORMATION_RETENTION_TYPES = {DetectionType.FACT_LOSS, DetectionType.OMISSION}
_RELEVANCE_TYPES = {DetectionType.TOPIC_DRIFT, DetectionType.REPETITION}
_TOOL_UTILIZATION_TYPES = {DetectionType.TOOL_RESULT_MISUSE}
_HALLUCINATION_RISK_TYPES = {DetectionType.UNSUPPORTED_CLAIM}

# Multiplies the per-signal penalty for `UNSUPPORTED_CLAIM` signals
# according to the specific evidence-based classification recorded by
# `ClaimSupportDetector` (see `app.analysis.semantic.detectors`) in
# `Signal.metadata["classification"]`. A signal that could not be
# classified (e.g. produced by some future detector without this
# metadata) falls back to the "unsupported" multiplier -- the least
# severe -- rather than being penalized as if it were a confirmed
# hallucination risk.
_HALLUCINATION_CLASSIFICATION_MULTIPLIERS = {
    "unsupported": 1.0,
    "contradicted": 1.3,
    "possible_hallucination": 1.6,
    "high_confidence_hallucination": 2.0,
}
_DEFAULT_HALLUCINATION_MULTIPLIER = 1.0


@dataclass(frozen=True)
class HealthScoreWeights:
    """Configuration for `compute_health_score`.

    `penalty_per_signal` is the base cost (before confidence/severity
    weighting) that a single matching signal contributes to its
    dimension's penalty. `dimension_weights` controls how much each
    dimension contributes to `overall_score` (a weight of 0 excludes a
    dimension from the overall score entirely, while still reporting it).
    Weights are relative, not required to sum to 1 -- the overall score is
    always a proper weighted average.
    """

    penalty_per_signal: float = 0.15
    dimension_weights: dict[str, float] = field(
        default_factory=lambda: {
            "consistency": 1.0,
            "instruction_adherence": 1.0,
            "information_retention": 1.0,
            "relevance": 1.0,
            "tool_utilization": 1.0,
            "hallucination_risk": 1.0,
        }
    )

    @classmethod
    def from_settings(cls, settings: Settings) -> HealthScoreWeights:
        """Build weights from environment-configured `Settings`.

        This is the only place that reads `app.config.Settings` for
        scoring purposes -- `compute_health_score` itself takes a plain
        `HealthScoreWeights` value so it stays free of any dependency on
        configuration loading and remains trivially unit-testable with
        arbitrary weight combinations.
        """
        return cls(
            penalty_per_signal=settings.health_penalty_per_signal,
            dimension_weights={
                "consistency": settings.health_weight_consistency,
                "instruction_adherence": settings.health_weight_instruction_adherence,
                "information_retention": (settings.health_weight_information_retention),
                "relevance": settings.health_weight_relevance,
                "tool_utilization": settings.health_weight_tool_utilization,
                "hallucination_risk": settings.health_weight_hallucination_risk,
            },
        )


DEFAULT_WEIGHTS = HealthScoreWeights()


@dataclass(frozen=True)
class HealthScoreResult:
    overall_score: float
    relevance_score: float
    consistency_score: float
    instruction_adherence_score: float
    information_retention_score: float
    tool_utilization_score: float
    hallucination_risk_score: float


def _penalty_for(signal: Signal, penalty_per_signal: float) -> float:
    multiplier = 1.0
    if signal.detection_type == DetectionType.UNSUPPORTED_CLAIM:
        classification = signal.metadata.get("classification")
        multiplier = _HALLUCINATION_CLASSIFICATION_MULTIPLIERS.get(
            classification, _DEFAULT_HALLUCINATION_MULTIPLIER
        )
    return signal.confidence * penalty_per_signal * multiplier


def _score_for(
    signals: list[Signal], types: set[DetectionType], penalty_per_signal: float
) -> float:
    relevant = [s for s in signals if s.detection_type in types]
    if not relevant:
        return 1.0
    penalty = sum(_penalty_for(s, penalty_per_signal) for s in relevant)
    return max(0.0, round(1.0 - penalty, 3))


def compute_health_score(
    signals: list[Signal], weights: HealthScoreWeights | None = None
) -> HealthScoreResult:
    weights = weights or DEFAULT_WEIGHTS
    penalty_per_signal = weights.penalty_per_signal

    consistency = _score_for(signals, _CONSISTENCY_TYPES, penalty_per_signal)
    instruction_adherence = _score_for(
        signals, _INSTRUCTION_ADHERENCE_TYPES, penalty_per_signal
    )
    information_retention = _score_for(
        signals, _INFORMATION_RETENTION_TYPES, penalty_per_signal
    )
    relevance = _score_for(signals, _RELEVANCE_TYPES, penalty_per_signal)
    tool_utilization = _score_for(signals, _TOOL_UTILIZATION_TYPES, penalty_per_signal)
    hallucination_risk = _score_for(
        signals, _HALLUCINATION_RISK_TYPES, penalty_per_signal
    )

    dimension_scores = {
        "consistency": consistency,
        "instruction_adherence": instruction_adherence,
        "information_retention": information_retention,
        "relevance": relevance,
        "tool_utilization": tool_utilization,
        "hallucination_risk": hallucination_risk,
    }
    total_weight = sum(
        weights.dimension_weights.get(name, 0.0) for name in dimension_scores
    )
    if total_weight <= 0:
        overall = round(sum(dimension_scores.values()) / len(dimension_scores), 3)
    else:
        weighted_sum = sum(
            score * weights.dimension_weights.get(name, 0.0)
            for name, score in dimension_scores.items()
        )
        overall = round(weighted_sum / total_weight, 3)

    return HealthScoreResult(
        overall_score=overall,
        relevance_score=relevance,
        consistency_score=consistency,
        instruction_adherence_score=instruction_adherence,
        information_retention_score=information_retention,
        tool_utilization_score=tool_utilization,
        hallucination_risk_score=hallucination_risk,
    )
