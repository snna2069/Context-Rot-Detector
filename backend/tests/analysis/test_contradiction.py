from __future__ import annotations

from app.analysis.detectors.contradiction import ContradictionDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_contradiction_detects_conflicting_restatement() -> None:
    messages = [
        make_message(1, MessageRole.USER, "When is the deadline?"),
        make_message(2, MessageRole.ASSISTANT, "The deadline is March 15th."),
        make_message(3, MessageRole.USER, "Can you confirm the deadline again?"),
        make_message(4, MessageRole.ASSISTANT, "The deadline is next Tuesday."),
    ]
    context = make_context(messages)

    signals = ContradictionDetector().detect(context)

    assert len(signals) == 1
    signal = signals[0]
    assert signal.metadata["subject"] == "deadline"
    assert 0.5 <= signal.confidence <= 0.85
    # A contradiction is evidence of inconsistency, never asserted as a
    # confirmed hallucination.
    assert "not confirmed proof" in signal.explanation
    assert "external_verification_available" in signal.metadata


def test_contradiction_flags_verification_available_when_tool_results_exist() -> None:
    from tests.analysis.helpers import make_tool_call

    tool_call = make_tool_call(
        message_id="tool-msg",
        tool_name="lookup_deadline",
        result_output={"deadline": "2026-03-15"},
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, "checking", tool_calls=(tool_call,)),
        make_message(2, MessageRole.ASSISTANT, "The deadline is March 15th."),
        make_message(3, MessageRole.ASSISTANT, "The deadline is next Tuesday."),
    ]
    context = make_context(messages)

    signals = ContradictionDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].metadata["external_verification_available"] is True


def test_contradiction_no_signal_for_consistent_restatement() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The deadline is March 15th."),
        make_message(2, MessageRole.ASSISTANT, "The deadline is March 15th."),
    ]
    context = make_context(messages)

    signals = ContradictionDetector().detect(context)

    assert signals == []


def test_contradiction_no_signal_for_single_mention() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The deadline is March 15th."),
    ]
    context = make_context(messages)

    signals = ContradictionDetector().detect(context)

    assert signals == []
