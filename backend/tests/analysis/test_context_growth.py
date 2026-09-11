from __future__ import annotations

from app.analysis.detectors.context_growth import ContextGrowthDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_context_growth_detects_accelerating_recent_messages() -> None:
    messages = [
        make_message(i, MessageRole.USER, "short message here") for i in range(1, 10)
    ]
    # Recent messages are dramatically longer than the historical average.
    for i in range(10, 16):
        messages.append(make_message(i, MessageRole.USER, "x" * 500))
    context = make_context(messages)

    signals = ContextGrowthDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence > 0


def test_context_growth_no_signal_for_steady_session() -> None:
    messages = [
        make_message(i, MessageRole.USER, "a steady length message every time")
        for i in range(1, 20)
    ]
    context = make_context(messages)

    signals = ContextGrowthDetector().detect(context)

    assert signals == []


def test_context_growth_no_signal_for_short_session() -> None:
    messages = [make_message(i, MessageRole.USER, "x" * 1000) for i in range(1, 5)]
    context = make_context(messages)

    signals = ContextGrowthDetector().detect(context)

    assert signals == []
