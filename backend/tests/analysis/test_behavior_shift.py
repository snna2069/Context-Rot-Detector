from __future__ import annotations

from app.analysis.detectors.behavior_shift import BehaviorShiftDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_behavior_shift_detects_sudden_length_deviation() -> None:
    messages = [
        make_message(i, MessageRole.ASSISTANT, "Reply. " + "word " * i)
        for i in range(1, 8)
    ]
    messages.append(make_message(8, MessageRole.ASSISTANT, "word " * 400))
    context = make_context(messages)

    signals = BehaviorShiftDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence > 0


def test_behavior_shift_no_signal_for_consistent_lengths() -> None:
    messages = [
        make_message(i, MessageRole.ASSISTANT, "A steady reply." + " word" * 5)
        for i in range(1, 10)
    ]
    context = make_context(messages)

    signals = BehaviorShiftDetector().detect(context)

    assert signals == []


def test_behavior_shift_no_signal_for_insufficient_history() -> None:
    messages = [
        make_message(i, MessageRole.ASSISTANT, "reply " * i) for i in range(1, 5)
    ]
    context = make_context(messages)

    signals = BehaviorShiftDetector().detect(context)

    assert signals == []
