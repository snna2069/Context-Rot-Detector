"""The analysis engine: runs every detector and aggregates their output.

Deliberately NOT a single monolithic `detect_context_rot()` function --
this is a thin runner over a list of independent, composable `Detector`
implementations (see `app.analysis.detectors`). Adding, removing, or
reordering a detector never affects the others.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from app.analysis.base import Detector
from app.analysis.context import SessionContext
from app.analysis.detectors import default_detectors
from app.analysis.health import (
    HealthScoreResult,
    HealthScoreWeights,
    compute_health_score,
)
from app.analysis.signals import Signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisResult:
    signals: list[Signal]
    health_score: HealthScoreResult


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
        for detector in self.detectors:
            try:
                signals.extend(detector.detect(context))
            except Exception:
                # One failing detector must never crash the whole analysis
                # run or block the other, unrelated detectors from reporting.
                logger.exception(
                    "Detector '%s' raised an exception during analysis of "
                    "session '%s'; skipping it for this run.",
                    getattr(detector, "name", detector.__class__.__name__),
                    context.session_id,
                )
        health_score = compute_health_score(signals, self.weights)
        return AnalysisResult(signals=signals, health_score=health_score)
