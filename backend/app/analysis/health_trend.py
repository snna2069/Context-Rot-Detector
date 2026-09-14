"""Trending a session's context-health score across analysis-run checkpoints.

Each `ContextHealthScore` row is one checkpoint measured at a specific
point in the session's growth (tied to the `AnalysisRun` that produced
it, which records the message-sequence range it analyzed). This module
answers the Phase 6 question directly: "was this session getting worse
as it became longer?" -- by regressing the overall score against both
checkpoint order (time) and, where available, context length (message
count analyzed).

This is a simple ordinary-least-squares slope over a handful of points,
not a statistical model with confidence intervals -- appropriate for a
prototype trend indicator, not a claim of statistical significance. No
new dependency (e.g. numpy/scipy) was introduced for this; the
regression is a few lines of pure Python.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TrendDirection = Literal["improving", "stable", "degrading"]

# A slope smaller in magnitude than this (score units per checkpoint) is
# treated as "stable" rather than a genuine trend -- score noise between
# runs of a few thousandths should not be reported as a direction.
_STABLE_SLOPE_EPSILON = 0.01

# Separate, smaller epsilon for the length-based slope: it is measured in
# score units per *message*, not per checkpoint, so its typical magnitude
# is naturally much smaller (a session can grow by dozens of messages
# between two checkpoints) and needs its own threshold.
_STABLE_LENGTH_SLOPE_EPSILON = 0.003


@dataclass(frozen=True)
class HealthTrendPoint:
    """One measured checkpoint, ready for trend analysis."""

    measured_at: datetime
    overall_score: float
    # Number of messages analyzed by the run that produced this score
    # (`AnalysisRun.input_sequence_end`), used as the proxy for "how long
    # the session had become" at this checkpoint. `None` when the
    # analysis run recorded no messages (e.g. an empty session).
    context_length: int | None = None


@dataclass(frozen=True)
class HealthTrendResult:
    direction: TrendDirection
    slope_per_checkpoint: float
    slope_per_context_length: float | None
    is_degrading_with_length: bool
    summary: str
    points: tuple[HealthTrendPoint, ...]


def _ols_slope(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Ordinary-least-squares slope of `ys` regressed on `xs`.

    Returns `None` when there are fewer than two distinct x-values (a
    slope is not meaningful with one data point, and is undefined when
    all x-values are identical).
    """
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return numerator / denominator


def analyze_health_trend(
    points: Sequence[HealthTrendPoint],
) -> HealthTrendResult:
    """Compute the trend across an ordered sequence of health checkpoints.

    `points` must already be sorted oldest-first (chronological order).
    """
    ordered = tuple(points)

    if len(ordered) < 2:
        return HealthTrendResult(
            direction="stable",
            slope_per_checkpoint=0.0,
            slope_per_context_length=None,
            is_degrading_with_length=False,
            summary=(
                "Not enough analysis runs yet to compute a trend "
                "(at least two are required)."
            ),
            points=ordered,
        )

    checkpoint_xs = list(range(len(ordered)))
    scores = [p.overall_score for p in ordered]
    slope_per_checkpoint = _ols_slope(checkpoint_xs, scores) or 0.0

    length_points = [
        (p.context_length, p.overall_score)
        for p in ordered
        if p.context_length is not None
    ]
    slope_per_length: float | None = None
    if len(length_points) >= 2:
        lengths = [float(lp[0]) for lp in length_points]
        length_scores = [lp[1] for lp in length_points]
        slope_per_length = _ols_slope(lengths, length_scores)

    if slope_per_checkpoint <= -_STABLE_SLOPE_EPSILON:
        direction: TrendDirection = "degrading"
    elif slope_per_checkpoint >= _STABLE_SLOPE_EPSILON:
        direction = "improving"
    else:
        direction = "stable"

    is_degrading_with_length = (
        slope_per_length is not None
        and slope_per_length <= -_STABLE_LENGTH_SLOPE_EPSILON
    )

    if is_degrading_with_length:
        summary = (
            "Context health has been declining as the session grew longer "
            f"(overall score changing by approximately {slope_per_length:.3f} "
            "per additional message analyzed)."
        )
    elif direction == "degrading":
        summary = (
            "Context health has been declining across recent analysis runs, "
            "though not clearly correlated with session length."
        )
    elif direction == "improving":
        summary = "Context health has been improving across recent analysis runs."
    else:
        summary = "Context health has remained roughly stable across recent runs."

    return HealthTrendResult(
        direction=direction,
        slope_per_checkpoint=round(slope_per_checkpoint, 4),
        slope_per_context_length=(
            round(slope_per_length, 6) if slope_per_length is not None else None
        ),
        is_degrading_with_length=is_degrading_with_length,
        summary=summary,
        points=ordered,
    )
