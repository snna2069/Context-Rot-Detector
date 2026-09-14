"""The provider-neutral semantic-analysis interface.

Every capability the pipeline needs from an LLM is expressed as one
narrow, independently-testable method here -- never one opaque
"analyze this session" call, and never a method that directly asks
"is this a hallucination?" (see `app.analysis.semantic.hallucination` for
why that question is only ever answered by our own aggregation logic).

Concrete implementations: `app.services.llm.unavailable.UnavailableAnalysisProvider`
(safe default when no LLM is configured) and
`app.services.llm.openai_provider.OpenAIAnalysisProvider` (a real HTTP-backed
provider for any OpenAI-compatible `/chat/completions` endpoint).
"""

from __future__ import annotations

from typing import Protocol

from app.services.llm.types import (
    ClaimSupportResult,
    ImportantFactsResult,
    InstructionDriftResult,
    RelevanceResult,
    SameFactResult,
    SemanticContradictionResult,
)


class AnalysisProvider(Protocol):
    """Semantic-analysis capabilities needed by the detection pipeline.

    Implementations must never raise for "the model doesn't know" -- they
    should return a low-confidence result instead. Implementations should
    raise `app.services.llm.errors.LLMProviderError` only for genuine
    infrastructure failures (network error, malformed response, timeout),
    which callers treat identically to "no answer available".
    """

    def extract_important_facts(self, text: str) -> ImportantFactsResult:
        """Extract the atomic claims/facts asserted in `text`."""
        ...

    def same_fact(self, statement_a: str, statement_b: str) -> SameFactResult:
        """Determine whether two statements refer to the same underlying
        fact/subject (regardless of phrasing)."""
        ...

    def detect_semantic_contradiction(
        self, statement_a: str, statement_b: str
    ) -> SemanticContradictionResult:
        """Determine whether two statements about the same fact conflict,
        beyond what lexical/regex comparison alone can detect."""
        ...

    def detect_instruction_drift(
        self, instruction: str, response: str
    ) -> InstructionDriftResult:
        """Determine whether `response` fails to follow `instruction`."""
        ...

    def assess_relevance(self, task: str, response: str) -> RelevanceResult:
        """Determine whether `response` is relevant to the current `task`
        (typically the most recent user request)."""
        ...

    def assess_claim_support(
        self, claim: str, evidence: tuple[str, ...]
    ) -> ClaimSupportResult:
        """Classify `claim` against `evidence` as SUPPORTED, CONTRADICTED,
        UNSUPPORTED, or INSUFFICIENT_EVIDENCE. Never asked to (and never
        able to, per `ClaimSupportResult`'s own validation) return a
        hallucination-risk label directly."""
        ...
