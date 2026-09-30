from __future__ import annotations

from app.analysis.detectors.contradiction import ContradictionDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_contradiction_detects_numeric_conflict_despite_similar_wording() -> None:
    """Regression for the lexical-similarity blind spot.

    "30 seconds" and "5 seconds" are 84% similar as strings, so the
    original purely lexical comparison scored them as *agreeing* -- the
    consistent phrasing around a changed number hid the conflict. Found
    by the evaluation corpus (see `evaluation/`).
    """
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The connection timeout is 30 seconds."),
        make_message(2, MessageRole.ASSISTANT, "The connection timeout is 5 seconds."),
    ]

    signals = ContradictionDetector().detect(make_context(messages))

    assert len(signals) == 1
    assert signals[0].metadata["comparison_basis"] == "numeric"
    assert signals[0].metadata["earlier_value"] == "30 seconds"
    assert signals[0].metadata["later_value"] == "5 seconds"


def test_contradiction_ignores_rewording_that_keeps_the_same_number() -> None:
    """Same number, different words, is not a factual conflict."""
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The retry limit is 3 attempts."),
        make_message(2, MessageRole.ASSISTANT, "The retry limit is 3 retries."),
    ]

    assert ContradictionDetector().detect(make_context(messages)) == []


def test_contradiction_suppressed_when_user_supplied_the_new_value() -> None:
    """Updating a fact the user corrected is correct behaviour, not rot."""
    messages = [
        make_message(1, MessageRole.USER, "When is the migration deadline?"),
        make_message(2, MessageRole.ASSISTANT, "The migration deadline is 14 March."),
        make_message(
            3,
            MessageRole.USER,
            "That is out of date, the migration deadline moved to 28 March.",
        ),
        make_message(4, MessageRole.ASSISTANT, "The migration deadline is 28 March."),
    ]

    assert ContradictionDetector().detect(make_context(messages)) == []


def test_contradiction_still_fires_when_user_did_not_supply_the_value() -> None:
    """The suppression must be narrow: an unprompted change still counts."""
    messages = [
        make_message(1, MessageRole.USER, "When is the migration deadline?"),
        make_message(2, MessageRole.ASSISTANT, "The migration deadline is 14 March."),
        make_message(3, MessageRole.USER, "Thanks, and who is leading it?"),
        make_message(4, MessageRole.ASSISTANT, "The migration deadline is 28 March."),
    ]

    signals = ContradictionDetector().detect(make_context(messages))

    assert len(signals) == 1


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
