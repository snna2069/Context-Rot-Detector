from __future__ import annotations

from app.analysis.detectors.fact_loss import FactLossDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_fact_loss_detects_hedge_after_established_fact() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The budget is five thousand dollars."),
        make_message(2, MessageRole.USER, "Remind me what the budget was?"),
        make_message(
            3, MessageRole.ASSISTANT, "I don't know what the budget is right now."
        ),
    ]
    context = make_context(messages)

    signals = FactLossDetector().detect(context)

    assert len(signals) == 1
    signal = signals[0]
    assert signal.metadata["subject"] == "budget"
    # The preceding user question also mentioned the subject, so the
    # stronger-link bonus should apply.
    assert signal.confidence == 0.7


def test_fact_loss_no_bonus_without_preceding_question() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The budget is five thousand dollars."),
        make_message(2, MessageRole.ASSISTANT, "Let's move on to scheduling."),
        make_message(
            3, MessageRole.ASSISTANT, "I don't know what the budget is right now."
        ),
    ]
    context = make_context(messages)

    signals = FactLossDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence == 0.55


def test_fact_loss_no_signal_when_no_hedge() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The budget is five thousand dollars."),
        make_message(2, MessageRole.USER, "Remind me what the budget was?"),
        make_message(3, MessageRole.ASSISTANT, "The budget is five thousand dollars."),
    ]
    context = make_context(messages)

    signals = FactLossDetector().detect(context)

    assert signals == []


def test_fact_loss_no_signal_without_established_fact() -> None:
    messages = [
        make_message(1, MessageRole.USER, "How are you?"),
        make_message(2, MessageRole.ASSISTANT, "I don't know what you mean."),
    ]
    context = make_context(messages)

    signals = FactLossDetector().detect(context)

    assert signals == []
