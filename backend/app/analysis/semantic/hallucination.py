"""Evidence-based hallucination-risk pipeline.

This module is the *only* place in the codebase allowed to produce a
`POSSIBLE_HALLUCINATION` or `HIGH_CONFIDENCE_HALLUCINATION` classification.
It never asks an LLM "did the agent hallucinate?" and trusts the answer.
Instead it asks only the narrow, verifiable-in-principle questions the
`AnalysisProvider` protocol exposes and combines their answers with a
deterministic Python priority-order aggregation (`_aggregate` below --
not another LLM call), so the final label is always traceable to concrete
supporting/contradicting evidence.

Pipeline
-----------------
    agent claim
        -> fact extraction            (provider.extract_important_facts)
        -> per-fact evidence support   (provider.assess_claim_support)
        -> deterministic aggregation   (this module)
        -> HallucinationAssessment

Every classification this module produces is probabilistic, derived
from the provider's own stated confidence per fact, unless independently
verified by a human or an external system -- it is never presented as
ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.llm.provider import AnalysisProvider
from app.services.llm.types import ClaimSupportResult, EvidenceClassification

# A CONTRADICTED fact at or above this confidence escalates the overall
# assessment from CONTRADICTED to HIGH_CONFIDENCE_HALLUCINATION.
HIGH_CONFIDENCE_CONTRADICTION_THRESHOLD = 0.75

# POSSIBLE_HALLUCINATION (a label this module derives, never one a
# provider returns directly) is deliberately capped below "high
# confidence": an unsupported claim is weaker evidence of fabrication
# than an outright contradiction.
POSSIBLE_HALLUCINATION_CONFIDENCE_CAP = 0.7


@dataclass(frozen=True)
class FactAssessment:
    """One extracted fact and how it compared against the evidence pool."""

    fact_text: str
    result: ClaimSupportResult


@dataclass(frozen=True)
class HallucinationAssessment:
    classification: EvidenceClassification
    confidence: float
    explanation: str
    fact_assessments: tuple[FactAssessment, ...] = ()


def assess_hallucination_risk(
    provider: AnalysisProvider,
    claim: str,
    evidence: tuple[str, ...],
) -> HallucinationAssessment:
    """Assess whether `claim` shows signs of being unsupported/fabricated,
    given the available `evidence` (typically nearby tool-result output).

    Design note: "no evidence at all" is treated as a *confident*
    INSUFFICIENT_EVIDENCE classification (confidence 1.0), not an
    uncertain one -- we are fully certain there is nothing to check the
    claim against. That is distinct from confidence *in the claim
    itself*, which this pipeline never asserts either way.
    """
    if not evidence:
        return HallucinationAssessment(
            classification=EvidenceClassification.INSUFFICIENT_EVIDENCE,
            confidence=1.0,
            explanation=(
                "No evidence was available to check this claim against, so "
                "no hallucination-risk judgment can be made either way."
            ),
            fact_assessments=(),
        )

    facts_result = provider.extract_important_facts(claim)
    fact_texts = tuple(f.text for f in facts_result.facts) or (claim,)

    assessments = tuple(
        FactAssessment(
            fact_text=fact_text,
            result=provider.assess_claim_support(fact_text, evidence),
        )
        for fact_text in fact_texts
    )
    return _aggregate(assessments)


def _aggregate(assessments: tuple[FactAssessment, ...]) -> HallucinationAssessment:
    if not assessments:
        return HallucinationAssessment(
            classification=EvidenceClassification.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            explanation="No facts could be extracted or assessed.",
            fact_assessments=(),
        )

    contradictions = [
        a
        for a in assessments
        if a.result.classification == EvidenceClassification.CONTRADICTED
    ]
    unsupported = [
        a
        for a in assessments
        if a.result.classification == EvidenceClassification.UNSUPPORTED
    ]
    supported = [
        a
        for a in assessments
        if a.result.classification == EvidenceClassification.SUPPORTED
    ]

    if contradictions:
        worst = max(contradictions, key=lambda a: a.result.confidence)
        if worst.result.confidence >= HIGH_CONFIDENCE_CONTRADICTION_THRESHOLD:
            return HallucinationAssessment(
                classification=EvidenceClassification.HIGH_CONFIDENCE_HALLUCINATION,
                confidence=worst.result.confidence,
                explanation=(
                    "An extracted fact was contradicted by available "
                    f"evidence with high confidence: {worst.result.explanation}"
                ),
                fact_assessments=assessments,
            )
        return HallucinationAssessment(
            classification=EvidenceClassification.CONTRADICTED,
            confidence=worst.result.confidence,
            explanation=(
                "An extracted fact was contradicted by available evidence: "
                f"{worst.result.explanation}"
            ),
            fact_assessments=assessments,
        )

    if unsupported:
        worst = max(unsupported, key=lambda a: a.result.confidence)
        capped_confidence = min(
            worst.result.confidence, POSSIBLE_HALLUCINATION_CONFIDENCE_CAP
        )
        return HallucinationAssessment(
            classification=EvidenceClassification.POSSIBLE_HALLUCINATION,
            confidence=capped_confidence,
            explanation=(
                "An extracted fact was not supported by any available "
                f"evidence: {worst.result.explanation} This is a possible "
                "hallucination, not a confirmed one -- no evidence "
                "contradicts the claim either."
            ),
            fact_assessments=assessments,
        )

    if len(supported) == len(assessments):
        avg_confidence = round(
            sum(a.result.confidence for a in supported) / len(supported), 3
        )
        return HallucinationAssessment(
            classification=EvidenceClassification.SUPPORTED,
            confidence=avg_confidence,
            explanation="Every extracted fact was supported by available evidence.",
            fact_assessments=assessments,
        )

    # Every fact came back INSUFFICIENT_EVIDENCE, or the provider had zero
    # confidence throughout (e.g. `UnavailableAnalysisProvider`).
    avg_confidence = round(
        sum(a.result.confidence for a in assessments) / len(assessments), 3
    )
    return HallucinationAssessment(
        classification=EvidenceClassification.INSUFFICIENT_EVIDENCE,
        confidence=avg_confidence,
        explanation=(
            "Available evidence did not clearly support, contradict, or "
            "address the extracted facts."
        ),
        fact_assessments=assessments,
    )
