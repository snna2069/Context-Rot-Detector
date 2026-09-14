"""Validates request construction and response parsing for
`OpenAIAnalysisProvider` using `httpx.MockTransport` -- no live API call,
per the project rule that unit tests must not require a live LLM."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.llm.errors import LLMProviderError
from app.services.llm.openai_provider import OpenAIAnalysisProvider
from app.services.llm.types import EvidenceClassification


def _client_with_response(payload: dict, status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    transport = httpx.MockTransport(handler)
    return httpx.Client(
        base_url="https://example.invalid/v1",
        transport=transport,
    )


def _chat_completion(content: dict) -> dict:
    return {
        "choices": [{"message": {"content": json.dumps(content)}}],
    }


def test_extract_important_facts_parses_response() -> None:
    client = _client_with_response(
        _chat_completion(
            {
                "facts": [{"text": "the deadline is March 15", "source_excerpt": None}],
                "confidence": 0.8,
                "explanation": "one clear factual claim",
            }
        )
    )
    provider = OpenAIAnalysisProvider(
        api_key="sk-test",
        base_url="https://example.invalid/v1",
        model="gpt-test",
        client=client,
    )

    result = provider.extract_important_facts("The deadline is March 15.")

    assert result.confidence == 0.8
    assert result.provider == "openai_compatible"
    assert result.model == "gpt-test"
    assert len(result.facts) == 1
    assert result.facts[0].text == "the deadline is March 15"


def test_assess_claim_support_maps_evidence_indexes() -> None:
    client = _client_with_response(
        _chat_completion(
            {
                "classification": "supported",
                "supporting_evidence_indexes": [1],
                "confidence": 0.9,
                "explanation": "matches evidence 1",
            }
        )
    )
    provider = OpenAIAnalysisProvider(
        api_key="sk-test",
        base_url="https://example.invalid/v1",
        model="gpt-test",
        client=client,
    )

    result = provider.assess_claim_support(
        "the deadline is March 15", ("unrelated snippet", "deadline: 2026-03-15")
    )

    assert result.classification == EvidenceClassification.SUPPORTED
    assert result.supporting_evidence_refs == ("deadline: 2026-03-15",)


def test_assess_claim_support_rejects_hallucination_label_from_model() -> None:
    """Even if the model ignores instructions and returns a
    hallucination-risk label directly, the provider must not pass it
    through -- it should fall back to INSUFFICIENT_EVIDENCE."""
    client = _client_with_response(
        _chat_completion(
            {
                "classification": "high_confidence_hallucination",
                "confidence": 0.95,
                "explanation": "misbehaving model",
            }
        )
    )
    provider = OpenAIAnalysisProvider(
        api_key="sk-test",
        base_url="https://example.invalid/v1",
        model="gpt-test",
        client=client,
    )

    result = provider.assess_claim_support("claim", ("evidence",))

    assert result.classification == EvidenceClassification.INSUFFICIENT_EVIDENCE


def test_non_2xx_response_raises_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = httpx.Client(
        base_url="https://example.invalid/v1", transport=httpx.MockTransport(handler)
    )
    provider = OpenAIAnalysisProvider(
        api_key="sk-test",
        base_url="https://example.invalid/v1",
        model="gpt-test",
        client=client,
    )

    with pytest.raises(LLMProviderError):
        provider.same_fact("a", "b")


def test_malformed_json_content_raises_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        )

    client = httpx.Client(
        base_url="https://example.invalid/v1", transport=httpx.MockTransport(handler)
    )
    provider = OpenAIAnalysisProvider(
        api_key="sk-test",
        base_url="https://example.invalid/v1",
        model="gpt-test",
        client=client,
    )

    with pytest.raises(LLMProviderError):
        provider.same_fact("a", "b")
