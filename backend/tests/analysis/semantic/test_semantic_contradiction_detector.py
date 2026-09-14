from __future__ import annotations

from app.analysis.semantic.detectors import SemanticContradictionDetector
from app.models import MessageRole
from app.services.llm.types import SameFactResult, SemanticContradictionResult
from tests.analysis.helpers import make_context, make_message
from tests.llm.fake_provider import ScriptedAnalysisProvider, result


def test_flags_semantically_contradictory_restatement() -> None:
    earlier = "We're going with PostgreSQL for the database."
    later = "We decided to use MongoDB instead of a relational database."
    provider = ScriptedAnalysisProvider(
        same_fact_by_pair={
            (earlier, later): SameFactResult(same=True, **result(0.8)),
        },
        contradiction_by_pair={
            (earlier, later): SemanticContradictionResult(
                is_contradiction=True, **result(0.75)
            ),
        },
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, earlier),
        make_message(2, MessageRole.ASSISTANT, later),
    ]

    signals = SemanticContradictionDetector(provider).detect(make_context(messages))

    assert len(signals) == 1
    assert signals[0].confidence == 0.75
    assert signals[0].metadata["provider"] == "scripted-test-double"


def test_no_signal_when_statements_are_not_the_same_fact() -> None:
    a = "The database is PostgreSQL."
    b = "The frontend uses React."
    provider = ScriptedAnalysisProvider(
        same_fact_by_pair={(a, b): SameFactResult(same=False, **result(0.9))},
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, a),
        make_message(2, MessageRole.ASSISTANT, b),
    ]

    signals = SemanticContradictionDetector(provider).detect(make_context(messages))

    assert signals == []


def test_no_signal_when_provider_confidence_too_low() -> None:
    a = "The database is PostgreSQL."
    b = "We use MongoDB now."
    provider = ScriptedAnalysisProvider(
        same_fact_by_pair={(a, b): SameFactResult(same=True, **result(0.3))},
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, a),
        make_message(2, MessageRole.ASSISTANT, b),
    ]

    signals = SemanticContradictionDetector(provider).detect(make_context(messages))

    assert signals == []


def test_no_signal_with_unavailable_provider_default() -> None:
    from app.services.llm.unavailable import UnavailableAnalysisProvider

    messages = [
        make_message(1, MessageRole.ASSISTANT, "The database is PostgreSQL."),
        make_message(2, MessageRole.ASSISTANT, "We use MongoDB now."),
    ]

    signals = SemanticContradictionDetector(UnavailableAnalysisProvider()).detect(
        make_context(messages)
    )

    assert signals == []
