from __future__ import annotations

from app.analysis.detectors.instruction_drift import InstructionDriftDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_instruction_drift_detects_literal_violation() -> None:
    messages = [
        make_message(
            1,
            MessageRole.SYSTEM,
            "Never mention pricing.",
        ),
        make_message(2, MessageRole.USER, "What can you tell me about the product?"),
        make_message(
            3,
            MessageRole.ASSISTANT,
            "Our pricing starts at $10 per month for the basic plan.",
        ),
    ]
    context = make_context(messages)

    signals = InstructionDriftDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence >= 0.6
    assert signals[0].metadata["forbidden_term"] == "pricing"


def test_instruction_drift_no_signal_when_directive_respected() -> None:
    messages = [
        make_message(
            1,
            MessageRole.SYSTEM,
            "Never mention pricing.",
        ),
        make_message(2, MessageRole.USER, "What can you tell me about the product?"),
        make_message(
            3,
            MessageRole.ASSISTANT,
            "It's a great productivity tool with many features.",
        ),
    ]
    context = make_context(messages)

    signals = InstructionDriftDetector().detect(context)

    assert signals == []


def test_instruction_drift_ignores_violation_before_directive() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "Our pricing starts at $10."),
        make_message(2, MessageRole.SYSTEM, "Never mention pricing in your responses."),
    ]
    context = make_context(messages)

    signals = InstructionDriftDetector().detect(context)

    assert signals == []
