from __future__ import annotations

import pytest

from app.services.llm.types import (
    ClaimSupportResult,
    EvidenceClassification,
    ImportantFactsResult,
    LLMTaskResult,
)


def test_llm_task_result_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        LLMTaskResult(
            confidence=1.5,
            explanation="x",
            provider="p",
            model="m",
        )


def test_llm_task_result_accepts_boundary_confidences() -> None:
    LLMTaskResult(confidence=0.0, explanation="x", provider="p", model="m")
    LLMTaskResult(confidence=1.0, explanation="x", provider="p", model="m")


def test_important_facts_result_defaults_to_no_facts() -> None:
    result = ImportantFactsResult(
        confidence=0.9, explanation="x", provider="p", model="m"
    )
    assert result.facts == ()


@pytest.mark.parametrize(
    "classification",
    [
        EvidenceClassification.SUPPORTED,
        EvidenceClassification.CONTRADICTED,
        EvidenceClassification.UNSUPPORTED,
        EvidenceClassification.INSUFFICIENT_EVIDENCE,
    ],
)
def test_claim_support_result_accepts_provider_assessable_classifications(
    classification: EvidenceClassification,
) -> None:
    result = ClaimSupportResult(
        confidence=0.7,
        explanation="x",
        provider="p",
        model="m",
        classification=classification,
    )
    assert result.classification == classification


@pytest.mark.parametrize(
    "classification",
    [
        EvidenceClassification.POSSIBLE_HALLUCINATION,
        EvidenceClassification.HIGH_CONFIDENCE_HALLUCINATION,
    ],
)
def test_claim_support_result_rejects_hallucination_labels(
    classification: EvidenceClassification,
) -> None:
    """A provider must never be able to construct a hallucination-risk
    label directly -- those labels may only come from
    `app.analysis.semantic.hallucination`'s own aggregation logic."""
    with pytest.raises(ValueError, match="must be one of"):
        ClaimSupportResult(
            confidence=0.9,
            explanation="x",
            provider="p",
            model="m",
            classification=classification,
        )
