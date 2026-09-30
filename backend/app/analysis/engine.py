"""The analysis engine: runs every detector and aggregates their output.

Deliberately NOT a single monolithic `detect_context_rot()` function --
this is a thin runner over a list of independent, composable `Detector`
implementations (see `app.analysis.detectors`). Adding, removing, or
reordering a detector never affects the others.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.analysis.base import Detector
from app.analysis.context import SessionContext
from app.analysis.detectors import default_detectors
from app.analysis.health import (
    HealthScoreResult,
    HealthScoreWeights,
    compute_health_score,
)
from app.analysis.signals import Signal
from app.models import DetectionType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectorOutcome:
    """Whether one detector actually completed during a run.

    A failed detector produces no signals, and "no signals" is otherwise
    indistinguishable from "looked and found nothing clean". Recording
    the outcome explicitly is what lets the rest of the pipeline avoid
    reporting an unassessed dimension as a healthy one.
    """

    detector_name: str
    detection_types: frozenset[DetectionType]
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class AnalysisResult:
    signals: list[Signal]
    health_score: HealthScoreResult
    outcomes: list[DetectorOutcome] = field(default_factory=list)

    @property
    def failed_outcomes(self) -> list[DetectorOutcome]:
        return [o for o in self.outcomes if not o.ok]

    @property
    def unassessed_types(self) -> frozenset[DetectionType]:
        """Detection types no detector managed to evaluate this run."""
        failed: set[DetectionType] = set()
        for outcome in self.failed_outcomes:
            failed |= outcome.detection_types
        return frozenset(failed)


class AnalysisEngine:
    def __init__(
        self,
        detectors: Sequence[Detector] | None = None,
        weights: HealthScoreWeights | None = None,
    ) -> None:
        self.detectors: list[Detector] = (
            list(detectors) if detectors is not None else default_detectors()
        )
        self.weights = weights

    def run(self, context: SessionContext) -> AnalysisResult:
        signals: list[Signal] = []
        outcomes: list[DetectorOutcome] = []
        for detector in self.detectors:
            name = getattr(detector, "name", detector.__class__.__name__)
            types = frozenset(getattr(detector, "detection_types", frozenset()))
            try:
                signals.extend(detector.detect(context))
            except Exception as exc:
                # One failing detector must never crash the whole analysis
                # run or block the other, unrelated detectors from reporting.
                # It must, however, be recorded: the dimensions this
                # detector covers are now UNASSESSED, not healthy.
                logger.exception(
                    "Detector '%s' raised an exception during analysis of "
                    "session '%s'; its detection types will be reported as "
                    "not assessed for this run.",
                    name,
                    context.session_id,
                )
                outcomes.append(
                    DetectorOutcome(
                        detector_name=name,
                        detection_types=types,
                        ok=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
            else:
                outcomes.append(
                    DetectorOutcome(detector_name=name, detection_types=types, ok=True)
                )

        unassessed: set[DetectionType] = set()
        assessed: set[DetectionType] = set()
        for outcome in outcomes:
            if outcome.ok:
                assessed |= outcome.detection_types
            else:
                unassessed |= outcome.detection_types

        # Only types covered by a detector that actually completed count
        # as assessed. A type whose detector failed -- or that no detector
        # covers at all -- must not be scored as clean.
        health_score = compute_health_score(
            signals, self.weights, assessed_types=frozenset(assessed - unassessed)
        )
        return AnalysisResult(
            signals=signals, health_score=health_score, outcomes=outcomes
        )
