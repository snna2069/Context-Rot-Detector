"""Tests for the evidence-based hallucination-risk aggregation pipeline.

Every classification path is exercised via `ScriptedAnalysisProvider` --
no live LLM is ever used to decide these outcomes, and none of these
tests assert that the *underlying claim* is true or false, only that the
pipeline classifies it correctly given scripted evidence-comparison
results.
"""

from __future__ import annotations

from app.analysis.semantic.hallucination import assess_hallucination_risk
from app.services.llm.types import (
    ClaimSupportResult,
    EvidenceClassification,
    ExtractedFact,
    ImportantFactsResult,
)
from tests.llm.fake_provider import MODEL_NAME, PROVIDER_NAME, ScriptedAnalysisProvider


def _facts(*texts: str) -> ImportantFactsResult:
    return ImportantFactsResult(
        confidence=0.9,
        explanation="extracted",
        provider=PROVIDER_NAME,
        model=MODEL_NAME,
        facts=tuple(ExtractedFact(text=t) for t in texts),
    )


def _support(
    classification: EvidenceClassification, confidence: float
) -> ClaimSupportResult:
    return ClaimSupportResult(
        confidence=confidence,
        explanation=f"scripted {classification.value}",
        provider=PROVIDER_NAME,
        model=MODEL_NAME,
        classification=classification,
    )


def test_no_evidence_is_confidently_insufficient() -> None:
    provider = ScriptedAnalysisProvider()

    assessment = assess_hallucination_risk(provider, "the sky is green", evidence=())

    assert assessment.classification == EvidenceClassification.INSUFFICIENT_EVIDENCE
    assert assessment.confidence == 1.0
    assert assessment.fact_assessments == ()


def test_all_facts_supported_yields_supported() -> None:
    claim = "The deadline is March 15 and the owner is Alice."
    provider = ScriptedAnalysisProvider(
        facts_by_text={claim: _facts("deadline is March 15", "owner is Alice")},
        claim_support_by_claim={
            "deadline is March 15": _support(EvidenceClassification.SUPPORTED, 0.9),
            "owner is Alice": _support(EvidenceClassification.SUPPORTED, 0.8),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("doc",))

    assert assessment.classification == EvidenceClassification.SUPPORTED
    assert assessment.confidence == 0.85


def test_low_confidence_contradiction_yields_contradicted() -> None:
    claim = "The deadline is April 1."
    provider = ScriptedAnalysisProvider(
        facts_by_text={claim: _facts("deadline is April 1")},
        claim_support_by_claim={
            "deadline is April 1": _support(EvidenceClassification.CONTRADICTED, 0.6),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("doc",))

    assert assessment.classification == EvidenceClassification.CONTRADICTED
    assert assessment.confidence == 0.6


def test_high_confidence_contradiction_escalates_to_high_confidence_hallucination() -> (
    None
):
    claim = "The deadline is April 1."
    provider = ScriptedAnalysisProvider(
        facts_by_text={claim: _facts("deadline is April 1")},
        claim_support_by_claim={
            "deadline is April 1": _support(EvidenceClassification.CONTRADICTED, 0.9),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("doc",))

    assert (
        assessment.classification
        == EvidenceClassification.HIGH_CONFIDENCE_HALLUCINATION
    )
    assert assessment.confidence == 0.9


def test_unsupported_fact_yields_possible_hallucination_capped_confidence() -> None:
    claim = "The system has 99.999% uptime."
    provider = ScriptedAnalysisProvider(
        facts_by_text={claim: _facts("system has 99.999% uptime")},
        claim_support_by_claim={
            "system has 99.999% uptime": _support(
                EvidenceClassification.UNSUPPORTED, 0.95
            ),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("doc",))

    assert assessment.classification == EvidenceClassification.POSSIBLE_HALLUCINATION
    # Confidence is capped even though the provider reported 0.95, since an
    # unsupported claim is weaker evidence than an outright contradiction.
    assert assessment.confidence == 0.7


def test_contradiction_takes_priority_over_unsupported() -> None:
    claim = "A and B."
    provider = ScriptedAnalysisProvider(
        facts_by_text={claim: _facts("fact a", "fact b")},
        claim_support_by_claim={
            "fact a": _support(EvidenceClassification.UNSUPPORTED, 0.5),
            "fact b": _support(EvidenceClassification.CONTRADICTED, 0.6),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("doc",))

    assert assessment.classification == EvidenceClassification.CONTRADICTED


def test_all_facts_insufficient_evidence_stays_insufficient() -> None:
    claim = "Some obscure claim."
    provider = ScriptedAnalysisProvider(
        facts_by_text={claim: _facts("obscure claim")},
        claim_support_by_claim={
            "obscure claim": _support(
                EvidenceClassification.INSUFFICIENT_EVIDENCE, 0.4
            ),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("unrelated",))

    assert assessment.classification == EvidenceClassification.INSUFFICIENT_EVIDENCE
    assert assessment.confidence == 0.4


def test_no_extracted_facts_falls_back_to_whole_claim() -> None:
    claim = "hello there"
    provider = ScriptedAnalysisProvider(
        claim_support_by_claim={
            claim: _support(EvidenceClassification.SUPPORTED, 0.7),
        },
    )

    assessment = assess_hallucination_risk(provider, claim, evidence=("doc",))

    assert len(assessment.fact_assessments) == 1
    assert assessment.fact_assessments[0].fact_text == claim
    assert assessment.classification == EvidenceClassification.SUPPORTED
