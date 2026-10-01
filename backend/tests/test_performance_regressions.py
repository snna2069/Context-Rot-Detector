"""Behavior-preserving performance regression tests for Phase 6."""

from __future__ import annotations

from time import perf_counter

from app.analysis.context import SessionContext
from app.analysis.detectors.behavior_shift import BehaviorShiftDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def _assistant_context(count: int) -> SessionContext:
    return make_context(
        [
            make_message(
                i,
                MessageRole.ASSISTANT,
                "reply " + ("x" * (i % 31 + 1)),
            )
            for i in range(1, count + 1)
        ]
    )


def test_behavior_shift_handles_four_thousand_messages_quickly() -> None:
    """The rolling mean/stdev path must remain linear in history length.

    The threshold is intentionally generous for shared CI runners. This is
    a regression guard against accidentally restoring the old O(n²)
    `fmean(lengths[:i])` / `pstdev(lengths[:i])` implementation, not a
    product latency SLO.
    """
    context = _assistant_context(4_000)

    started = perf_counter()
    signals = BehaviorShiftDetector().detect(context)
    elapsed = perf_counter() - started

    assert isinstance(signals, list)
    assert elapsed < 1.0


def test_behavior_shift_keeps_short_history_behavior() -> None:
    context = _assistant_context(6)

    assert BehaviorShiftDetector().detect(context) == []
