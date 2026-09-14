"""Result types shared by every `AnalysisProvider` implementation.

Every dataclass here carries `confidence`, `explanation`, and
`provider`/`model` metadata, per the project rule that every LLM-generated
analysis must be explainable and attributable. None of these types are
persisted directly -- `app.analysis.semantic.detectors` turns them into
ordinary `app.analysis.signals.Signal` instances (with the provider/model
recorded in `Signal.metadata`) so the rest of the pipeline never needs to
know an LLM was involved.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceClassification(StrEnum):
    """How a claim relates to the evidence gathered to check it.

    Only the first four values may ever be returned directly by an
    `AnalysisProvider` (see `PROVIDER_ASSESSABLE_CLASSIFICATIONS`). The
    last two are hallucination-*risk* labels and may only be produced by
    `app.analysis.semantic.hallucination.assess_hallucination_risk`'s own
    deterministic aggregation logic -- this codebase never asks an LLM
    "did the agent hallucinate?" and trusts the answer.
    """

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    POSSIBLE_HALLUCINATION = "possible_hallucination"
    HIGH_CONFIDENCE_HALLUCINATION = "high_confidence_hallucination"


PROVIDER_ASSESSABLE_CLASSIFICATIONS = frozenset(
    {
        EvidenceClassification.SUPPORTED,
        EvidenceClassification.CONTRADICTED,
        EvidenceClassification.UNSUPPORTED,
        EvidenceClassification.INSUFFICIENT_EVIDENCE,
    }
)


def _validate_confidence(confidence: float) -> None:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be within [0, 1], got {confidence!r}")


@dataclass(frozen=True)
class LLMTaskResult:
    """Fields every provider-produced result must carry.

    `confidence` is the provider's own confidence in the task-specific
    fields declared on the subclass -- like a deterministic `Signal`'s
    confidence, it is never a claim about external truth.
    `explanation` must be phrasing suitable to show directly in the UI.
    """

    confidence: float
    explanation: str
    provider: str
    model: str

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)


@dataclass(frozen=True)
class ExtractedFact:
    """A single atomic claim extracted from a longer piece of text."""

    text: str
    source_excerpt: str | None = None


@dataclass(frozen=True)
class ImportantFactsResult(LLMTaskResult):
    facts: tuple[ExtractedFact, ...] = ()


@dataclass(frozen=True)
class SameFactResult(LLMTaskResult):
    """Whether two statements refer to the same underlying fact/subject."""

    same: bool = False


@dataclass(frozen=True)
class SemanticContradictionResult(LLMTaskResult):
    """Whether two statements (already known to be about the same fact)
    conflict with each other, beyond what lexical comparison can tell."""

    is_contradiction: bool = False


@dataclass(frozen=True)
class InstructionDriftResult(LLMTaskResult):
    """Whether a response fails to follow an established instruction."""

    drifted: bool = False


@dataclass(frozen=True)
class RelevanceResult(LLMTaskResult):
    """Whether a response is on-topic for the current task/user request."""

    is_relevant: bool = True


@dataclass(frozen=True)
class ClaimSupportResult(LLMTaskResult):
    """The result of comparing one claim against a pool of evidence.

    `classification` is restricted at construction time to the four
    provider-assessable values -- this is the concrete enforcement of the
    hallucination-safety rule: a provider implementation literally cannot
    construct a `ClaimSupportResult` labelled as a hallucination-risk
    classification, even by mistake.
    """

    classification: EvidenceClassification = (
        EvidenceClassification.INSUFFICIENT_EVIDENCE
    )
    supporting_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.classification not in PROVIDER_ASSESSABLE_CLASSIFICATIONS:
            raise ValueError(
                "ClaimSupportResult.classification must be one of "
                f"{sorted(PROVIDER_ASSESSABLE_CLASSIFICATIONS)}, got "
                f"{self.classification!r}. Hallucination-risk labels may "
                "only be produced by "
                "app.analysis.semantic.hallucination's own aggregation "
                "logic, never returned directly by a provider."
            )
