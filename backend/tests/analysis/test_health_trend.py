"""Unit tests for `app.analysis.health_trend.analyze_health_trend`.

Covers the scenarios named in the Phase 6 brief: healthy (stable),
gradually degrading, isolated anomaly (single dip that doesn't establish
a trend), and severe/sustained degradation -- plus the length-correlated
"getting worse as it became longer" question specifically.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.analysis.health_trend import HealthTrendPoint, analyze_health_trend

_START = datetime(2026, 1, 1, tzinfo=UTC)


def _point(minute: int, score: float, length: int | None) -> HealthTrendPoint:
    return HealthTrendPoint(
        measured_at=_START + timedelta(minutes=minute),
        overall_score=score,
        context_length=length,
    )


def test_fewer_than_two_points_reports_stable_with_explanation() -> None:
    result = analyze_health_trend([_point(0, 0.9, 5)])

    assert result.direction == "stable"
    assert "Not enough analysis runs" in result.summary
    assert result.is_degrading_with_length is False


def test_healthy_session_with_flat_scores_is_stable() -> None:
    points = [_point(i, 0.95, 10 + i) for i in range(5)]

    result = analyze_health_trend(points)

    assert result.direction == "stable"
    assert result.is_degrading_with_length is False


def test_gradually_degrading_session_is_flagged_as_degrading_with_length() -> None:
    points = [
        _point(0, 0.95, 10),
        _point(1, 0.85, 25),
        _point(2, 0.70, 40),
        _point(3, 0.55, 55),
        _point(4, 0.40, 70),
    ]

    result = analyze_health_trend(points)

    assert result.direction == "degrading"
    assert result.is_degrading_with_length is True
    assert result.slope_per_context_length is not None
    assert result.slope_per_context_length < 0
    assert "declining as the session grew longer" in result.summary


def test_isolated_anomaly_does_not_dominate_an_otherwise_stable_trend() -> None:
    # One low outlier in the middle of an otherwise flat, healthy series.
    points = [
        _point(0, 0.95, 10),
        _point(1, 0.94, 20),
        _point(2, 0.55, 30),  # isolated anomaly
        _point(3, 0.95, 40),
        _point(4, 0.94, 50),
    ]

    result = analyze_health_trend(points)

    # The overall linear trend across the whole series should stay close
    # to flat -- a single anomaly should not be reported as a sustained
    # decline the way a gradual, monotonic decline is.
    assert abs(result.slope_per_checkpoint) < 0.05


def test_severe_sustained_degradation_has_a_steep_negative_slope() -> None:
    points = [
        _point(0, 0.9, 10),
        _point(1, 0.5, 40),
        _point(2, 0.2, 70),
        _point(3, 0.05, 100),
    ]

    result = analyze_health_trend(points)

    assert result.direction == "degrading"
    assert result.is_degrading_with_length is True
    assert result.slope_per_checkpoint < -0.1


def test_improving_session_is_reported_as_improving() -> None:
    points = [_point(i, 0.4 + i * 0.1, 10 + i) for i in range(5)]

    result = analyze_health_trend(points)

    assert result.direction == "improving"
    assert result.is_degrading_with_length is False


def test_missing_context_length_skips_length_correlation_gracefully() -> None:
    points = [_point(i, 0.9 - i * 0.1, None) for i in range(4)]

    result = analyze_health_trend(points)

    assert result.direction == "degrading"
    assert result.slope_per_context_length is None
    assert result.is_degrading_with_length is False
