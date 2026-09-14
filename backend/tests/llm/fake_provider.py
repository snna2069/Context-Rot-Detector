"""In-memory `AnalysisProvider` test double for deterministic tests.

Never makes a network call. Every method looks up its answer from a
per-call-signature mapping supplied at construction time; any input not
explicitly scripted falls back to the same safe/negative, zero-confidence
behavior as `UnavailableAnalysisProvider`, so unscripted calls are
harmless rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.llm.types import (
    ClaimSupportResult,
    EvidenceClassification,
    ImportantFactsResult,
    InstructionDriftResult,
    RelevanceResult,
    SameFactResult,
    SemanticContradictionResult,
)

PROVIDER_NAME = "scripted-test-double"
MODEL_NAME = "scripted-model"


@dataclass
class ScriptedAnalysisProvider:
    """Script exact expected outputs per call, keyed by the call's inputs.

    Each `*_by_*` mapping is consulted first; if the given input tuple is
    not present, a safe default (mirroring `UnavailableAnalysisProvider`)
    is returned instead, so tests only need to script the specific inputs
    they care about.
    """

    facts_by_text: dict[str, ImportantFactsResult] = field(default_factory=dict)
    same_fact_by_pair: dict[tuple[str, str], SameFactResult] = field(
        default_factory=dict
    )
    contradiction_by_pair: dict[tuple[str, str], SemanticContradictionResult] = field(
        default_factory=dict
    )
    drift_by_pair: dict[tuple[str, str], InstructionDriftResult] = field(
        default_factory=dict
    )
    relevance_by_pair: dict[tuple[str, str], RelevanceResult] = field(
        default_factory=dict
    )
    claim_support_by_claim: dict[str, ClaimSupportResult] = field(default_factory=dict)

    def extract_important_facts(self, text: str) -> ImportantFactsResult:
        if text in self.facts_by_text:
            return self.facts_by_text[text]
        return ImportantFactsResult(
            confidence=0.0,
            explanation="not scripted",
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            facts=(),
        )

    def same_fact(self, statement_a: str, statement_b: str) -> SameFactResult:
        result = self.same_fact_by_pair.get((statement_a, statement_b))
        if result is not None:
            return result
        return SameFactResult(
            confidence=0.0,
            explanation="not scripted",
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            same=False,
        )

    def detect_semantic_contradiction(
        self, statement_a: str, statement_b: str
    ) -> SemanticContradictionResult:
        result = self.contradiction_by_pair.get((statement_a, statement_b))
        if result is not None:
            return result
        return SemanticContradictionResult(
            confidence=0.0,
            explanation="not scripted",
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            is_contradiction=False,
        )

    def detect_instruction_drift(
        self, instruction: str, response: str
    ) -> InstructionDriftResult:
        result = self.drift_by_pair.get((instruction, response))
        if result is not None:
            return result
        return InstructionDriftResult(
            confidence=0.0,
            explanation="not scripted",
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            drifted=False,
        )

    def assess_relevance(self, task: str, response: str) -> RelevanceResult:
        result = self.relevance_by_pair.get((task, response))
        if result is not None:
            return result
        return RelevanceResult(
            confidence=0.0,
            explanation="not scripted",
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            is_relevant=True,
        )

    def assess_claim_support(
        self, claim: str, evidence: tuple[str, ...]
    ) -> ClaimSupportResult:
        result = self.claim_support_by_claim.get(claim)
        if result is not None:
            return result
        return ClaimSupportResult(
            confidence=0.0,
            explanation="not scripted",
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            classification=EvidenceClassification.INSUFFICIENT_EVIDENCE,
            supporting_evidence_refs=(),
        )


def result(
    confidence: float,
    explanation: str = "scripted",
    **kwargs: object,
) -> dict[str, object]:
    """Small helper so test call-sites don't need to repeat provider/model."""
    return {
        "confidence": confidence,
        "explanation": explanation,
        "provider": PROVIDER_NAME,
        "model": MODEL_NAME,
        **kwargs,
    }
