"""`UnavailableAnalysisProvider` must always return a safe, zero-confidence
result -- it is the fallback used whenever no LLM is configured, and every
semantic detector relies on its confidence being below their emission
threshold so that "no LLM configured" naturally means "no semantic
signals", with no special-casing anywhere else."""

from __future__ import annotations

from app.services.llm.types import EvidenceClassification
from app.services.llm.unavailable import UnavailableAnalysisProvider


def test_unavailable_provider_returns_zero_confidence_for_every_task() -> None:
    provider = UnavailableAnalysisProvider()

    assert provider.extract_important_facts("anything").confidence == 0.0
    assert provider.same_fact("a", "b").confidence == 0.0
    assert provider.detect_semantic_contradiction("a", "b").confidence == 0.0
    assert provider.detect_instruction_drift("do x", "did y").confidence == 0.0
    assert provider.assess_relevance("task", "reply").confidence == 0.0
    assert provider.assess_claim_support("claim", ("evidence",)).confidence == 0.0


def test_unavailable_provider_never_asserts_a_problem() -> None:
    provider = UnavailableAnalysisProvider()

    assert provider.same_fact("a", "b").same is False
    assert provider.detect_semantic_contradiction("a", "b").is_contradiction is False
    assert provider.detect_instruction_drift("x", "y").drifted is False
    assert provider.assess_relevance("x", "y").is_relevant is True
    assert (
        provider.assess_claim_support("c", ("e",)).classification
        == EvidenceClassification.INSUFFICIENT_EVIDENCE
    )
