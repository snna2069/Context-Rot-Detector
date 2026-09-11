from __future__ import annotations

from app.analysis.detectors.omission import OmissionDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_omission_detects_dropped_important_information() -> None:
    messages = [
        make_message(
            1,
            MessageRole.USER,
            "Important: the patient is allergic to penicillin.",
        ),
        make_message(
            2,
            MessageRole.USER,
            "What medication should be prescribed for the patient?",
        ),
        make_message(
            3, MessageRole.ASSISTANT, "I recommend acetaminophen for pain relief."
        ),
    ]
    context = make_context(messages)

    signals = OmissionDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence >= 0.5


def test_omission_no_signal_when_information_restated() -> None:
    messages = [
        make_message(
            1,
            MessageRole.USER,
            "Important: the patient is allergic to penicillin.",
        ),
        make_message(
            2,
            MessageRole.USER,
            "What medication should be prescribed for the patient?",
        ),
        make_message(
            3,
            MessageRole.ASSISTANT,
            "Since the patient is allergic to penicillin, I recommend "
            "acetaminophen instead.",
        ),
    ]
    context = make_context(messages)

    signals = OmissionDetector().detect(context)

    assert signals == []


def test_omission_no_signal_for_unrelated_follow_up() -> None:
    messages = [
        make_message(
            1,
            MessageRole.USER,
            "Important: the patient is allergic to penicillin.",
        ),
        make_message(2, MessageRole.USER, "What's the weather like today?"),
        make_message(3, MessageRole.ASSISTANT, "It's sunny and warm outside."),
    ]
    context = make_context(messages)

    signals = OmissionDetector().detect(context)

    assert signals == []


def test_omission_no_signal_without_marker_phrase() -> None:
    messages = [
        make_message(1, MessageRole.USER, "The patient is allergic to penicillin."),
        make_message(
            2,
            MessageRole.USER,
            "What medication should be prescribed for the patient?",
        ),
        make_message(
            3, MessageRole.ASSISTANT, "I recommend acetaminophen for pain relief."
        ),
    ]
    context = make_context(messages)

    signals = OmissionDetector().detect(context)

    assert signals == []
