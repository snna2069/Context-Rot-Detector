"""Composite context-health scoring.

Turns the raw list of `Signal`s produced by the detectors into the four
sub-scores tracked by `ContextHealthScore` plus an overall score, so health
can be trended over time per session (one row per analysis run).

Design notes
-----------------
- Every sub-score is in [0, 1], where 1.0 means "no evidence of a problem
  in this dimension" and 0.0 means "maximum observed evidence of a
  problem." These are deliberately *relative* scores derived from the
  signals actually raised in this run, not calibrated against any external
  ground truth -- they are a summary of the detectors' own findings, not
  an independent judgment.
- `CONTEXT_GROWTH` and `TOPIC_DRIFT`/`BEHAVIOR_SHIFT` signals are
  informational trend signals and are intentionally excluded from the
  penalty-based sub-scores below; they are surfaced as detection events
  but do not by themselves reduce the health score, per the instruction
  to never treat length/growth alone as rot.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.analysis.signals import Signal
from app.models import DetectionType

# Detection types that reduce each sub-score, and how much each
# occurrence "costs" (before severity/confidence weighting).
_CONSISTENCY_TYPES = {DetectionType.CONTRADICTION, DetectionType.FACT_LOSS}
_INSTRUCTION_ADHERENCE_TYPES = {
    DetectionType.INSTRUCTION_DRIFT,
    DetectionType.OMISSION,
}
_RELEVANCE_TYPES = {DetectionType.TOPIC_DRIFT, DetectionType.REPETITION}
_EVIDENCE_COVERAGE_TYPES = {DetectionType.TOOL_RESULT_MISUSE}

_PENALTY_PER_SIGNAL = 0.15


@dataclass(frozen=True)
class HealthScoreResult:
    overall_score: float
    relevance_score: float
    consistency_score: float
    instruction_adherence_score: float
    evidence_coverage_score: float


def _score_for(signals: list[Signal], types: set[DetectionType]) -> float:
    relevant = [s for s in signals if s.detection_type in types]
    if not relevant:
        return 1.0
    penalty = sum(s.confidence * _PENALTY_PER_SIGNAL for s in relevant)
    return max(0.0, round(1.0 - penalty, 3))


def compute_health_score(signals: list[Signal]) -> HealthScoreResult:
    consistency = _score_for(signals, _CONSISTENCY_TYPES)
    instruction_adherence = _score_for(signals, _INSTRUCTION_ADHERENCE_TYPES)
    relevance = _score_for(signals, _RELEVANCE_TYPES)
    evidence_coverage = _score_for(signals, _EVIDENCE_COVERAGE_TYPES)

    overall = round(
        (consistency + instruction_adherence + relevance + evidence_coverage) / 4,
        3,
    )
    return HealthScoreResult(
        overall_score=overall,
        relevance_score=relevance,
        consistency_score=consistency,
        instruction_adherence_score=instruction_adherence,
        evidence_coverage_score=evidence_coverage,
    )
