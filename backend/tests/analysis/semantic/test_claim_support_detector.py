from __future__ import annotations

from app.analysis.semantic.detectors import ClaimSupportDetector
from app.models import DetectionType, MessageRole
from app.services.llm.types import (
    ClaimSupportResult,
    EvidenceClassification,
    ExtractedFact,
    ImportantFactsResult,
)
from tests.analysis.helpers import make_context, make_message, make_tool_call
from tests.llm.fake_provider import ScriptedAnalysisProvider, result


def test_skips_entire_session_with_no_tool_results() -> None:
    provider = ScriptedAnalysisProvider()
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The server has 99.99% uptime."),
    ]

    signals = ClaimSupportDetector(provider).detect(make_context(messages))

    assert signals == []


def test_flags_unsupported_claim_against_tool_result_evidence() -> None:
    claim = "The server has 99.999% uptime this month."
    tool_call = make_tool_call(
        message_id="tool-msg",
        tool_name="get_uptime",
        result_output={"uptime_percent": 97.2},
    )
    provider = ScriptedAnalysisProvider(
        facts_by_text={
            claim: ImportantFactsResult(
                facts=(ExtractedFact(text="server has 99.999% uptime this month"),),
                **result(0.9),
            )
        },
        claim_support_by_claim={
            "server has 99.999% uptime this month": ClaimSupportResult(
                classification=EvidenceClassification.UNSUPPORTED,
                **result(0.8),
            ),
        },
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, "checking", tool_calls=(tool_call,)),
        make_message(2, MessageRole.ASSISTANT, claim),
    ]

    signals = ClaimSupportDetector(provider).detect(make_context(messages))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.detection_type == DetectionType.UNSUPPORTED_CLAIM
    assert signal.metadata["classification"] == "possible_hallucination"
    assert "probabilistic" in signal.explanation


def test_no_signal_for_supported_claim() -> None:
    claim = "The server had 97% uptime this month."
    tool_call = make_tool_call(
        message_id="tool-msg",
        tool_name="get_uptime",
        result_output={"uptime_percent": 97.0},
    )
    provider = ScriptedAnalysisProvider(
        facts_by_text={
            claim: ImportantFactsResult(
                facts=(ExtractedFact(text="server had 97% uptime this month"),),
                **result(0.9),
            )
        },
        claim_support_by_claim={
            "server had 97% uptime this month": ClaimSupportResult(
                classification=EvidenceClassification.SUPPORTED,
                **result(0.85),
            ),
        },
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, "checking", tool_calls=(tool_call,)),
        make_message(2, MessageRole.ASSISTANT, claim),
    ]

    signals = ClaimSupportDetector(provider).detect(make_context(messages))

    assert signals == []


def test_ignores_messages_with_no_preceding_evidence_in_window() -> None:
    provider = ScriptedAnalysisProvider()
    tool_call = make_tool_call(
        message_id="tool-msg",
        tool_name="get_uptime",
        result_output={"uptime_percent": 97.0},
    )
    messages = [
        make_message(1, MessageRole.ASSISTANT, "checking", tool_calls=(tool_call,)),
        make_message(2, MessageRole.USER, "thanks"),
        make_message(3, MessageRole.ASSISTANT, "You're welcome!"),
    ]

    signals = ClaimSupportDetector(provider).detect(make_context(messages))

    # "You're welcome!" has evidence in its lookback window (the tool
    # result), but the scripted provider defaults to INSUFFICIENT_EVIDENCE
    # with 0 confidence for unscripted claims, which is never emitted.
    assert signals == []
