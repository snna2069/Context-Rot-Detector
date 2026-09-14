from __future__ import annotations

from app.analysis.semantic.detectors import SemanticRelevanceDetector
from app.models import MessageRole
from app.services.llm.types import RelevanceResult
from tests.analysis.helpers import make_context, make_message
from tests.llm.fake_provider import ScriptedAnalysisProvider, result


def test_flags_irrelevant_reply() -> None:
    task = "What is the capital of France?"
    reply = "Here is a recipe for chocolate cake."
    provider = ScriptedAnalysisProvider(
        relevance_by_pair={
            (task, reply): RelevanceResult(is_relevant=False, **result(0.85)),
        },
    )
    messages = [
        make_message(1, MessageRole.USER, task),
        make_message(2, MessageRole.ASSISTANT, reply),
    ]

    signals = SemanticRelevanceDetector(provider).detect(make_context(messages))

    assert len(signals) == 1
    assert signals[0].confidence == 0.85


def test_no_signal_for_relevant_reply() -> None:
    task = "What is the capital of France?"
    reply = "The capital of France is Paris."
    provider = ScriptedAnalysisProvider(
        relevance_by_pair={
            (task, reply): RelevanceResult(is_relevant=True, **result(0.9)),
        },
    )
    messages = [
        make_message(1, MessageRole.USER, task),
        make_message(2, MessageRole.ASSISTANT, reply),
    ]

    signals = SemanticRelevanceDetector(provider).detect(make_context(messages))

    assert signals == []


def test_no_signal_when_no_following_assistant_reply() -> None:
    provider = ScriptedAnalysisProvider()
    messages = [make_message(1, MessageRole.USER, "hello?")]

    signals = SemanticRelevanceDetector(provider).detect(make_context(messages))

    assert signals == []
