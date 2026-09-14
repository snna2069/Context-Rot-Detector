"""The safe default provider used when no LLM is configured.

This is a legitimate Null Object, not "fake AI": every method returns an
honest, zero/near-zero-confidence result rather than fabricating a
finding. Because every semantic detector already ignores low-confidence
results, wiring this provider in means the semantic detectors run and
naturally emit no signals -- there is no separate "is an LLM configured?"
branch anywhere else in the codebase.
"""

from __future__ import annotations

from app.services.llm.types import (
    ClaimSupportResult,
    EvidenceClassification,
    ImportantFactsResult,
    InstructionDriftResult,
    RelevanceResult,
    SameFactResult,
    SemanticContradictionResult,
)

PROVIDER_NAME = "unavailable"
MODEL_NAME = "none"

_NO_PROVIDER_EXPLANATION = (
    "No LLM provider is configured (LLM_API_KEY is unset), so semantic "
    "analysis was not performed for this input."
)


class UnavailableAnalysisProvider:
    """Returns a safe, zero-confidence result for every capability."""

    def extract_important_facts(self, text: str) -> ImportantFactsResult:
        return ImportantFactsResult(
            confidence=0.0,
            explanation=_NO_PROVIDER_EXPLANATION,
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            facts=(),
        )

    def same_fact(self, statement_a: str, statement_b: str) -> SameFactResult:
        return SameFactResult(
            confidence=0.0,
            explanation=_NO_PROVIDER_EXPLANATION,
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            same=False,
        )

    def detect_semantic_contradiction(
        self, statement_a: str, statement_b: str
    ) -> SemanticContradictionResult:
        return SemanticContradictionResult(
            confidence=0.0,
            explanation=_NO_PROVIDER_EXPLANATION,
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            is_contradiction=False,
        )

    def detect_instruction_drift(
        self, instruction: str, response: str
    ) -> InstructionDriftResult:
        return InstructionDriftResult(
            confidence=0.0,
            explanation=_NO_PROVIDER_EXPLANATION,
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            drifted=False,
        )

    def assess_relevance(self, task: str, response: str) -> RelevanceResult:
        return RelevanceResult(
            confidence=0.0,
            explanation=_NO_PROVIDER_EXPLANATION,
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            is_relevant=True,
        )

    def assess_claim_support(
        self, claim: str, evidence: tuple[str, ...]
    ) -> ClaimSupportResult:
        return ClaimSupportResult(
            confidence=0.0,
            explanation=_NO_PROVIDER_EXPLANATION,
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            classification=EvidenceClassification.INSUFFICIENT_EVIDENCE,
            supporting_evidence_refs=(),
        )
