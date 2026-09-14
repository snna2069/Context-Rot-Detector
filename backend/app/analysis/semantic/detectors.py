"""Semantic detectors: same `Detector` protocol as the deterministic ones,
but each is constructor-injected with an `AnalysisProvider` and calls out
to it for the parts of the analysis that genuinely need language
understanding rather than lexical pattern matching.

Design notes shared by every detector in this module
-----------------------------------------------------
- All comparisons use a small, bounded lookback/lookahead window (see the
  `*_WINDOW` constants) rather than exhaustively comparing every pair of
  messages in a session. This bounds the number of LLM calls per analysis
  run at the cost of missing long-range relationships -- a deliberate,
  documented tradeoff (see each class's docstring).
- Every result is only turned into a `Signal` if the provider's own
  confidence clears `MIN_EMIT_CONFIDENCE`. This is what makes it safe to
  always include these detectors in the engine's detector list: when
  `UnavailableAnalysisProvider` is wired in (no LLM configured), every
  call returns confidence 0.0 and no detector below ever emits a signal.
- None of these detectors persist provider/model identity onto dedicated
  columns (no schema change was made for Phase 5) -- it is recorded in
  `Signal.metadata["provider"]` / `["model"]`, consistent with how
  detector-specific context is already surfaced for the deterministic
  detectors.
"""

from __future__ import annotations

from app.analysis.base import Detector
from app.analysis.context import SessionContext
from app.analysis.semantic.hallucination import assess_hallucination_risk
from app.analysis.signals import Evidence, Signal
from app.models import DetectionSeverity, DetectionType, MessageRole
from app.services.llm.provider import AnalysisProvider
from app.services.llm.types import EvidenceClassification

MIN_EMIT_CONFIDENCE = 0.5

CONTRADICTION_LOOKBACK = 6
INSTRUCTION_LOOKAHEAD = 5
CLAIM_SUPPORT_LOOKBACK_MESSAGES = 8

_INSTRUCTION_ROLES = {MessageRole.SYSTEM, MessageRole.DEVELOPER}

_EXCERPT_LEN = 200


class SemanticContradictionDetector:
    """Compares assistant statements for meaning-level (not just lexical)
    contradiction.

    Complements the deterministic `ContradictionDetector`, which only
    catches statements matching a narrow "<subject> is <value>" regex.
    This detector instead asks the provider whether two statements are
    about the same underlying fact (`same_fact`) and, if so, whether they
    conflict (`detect_semantic_contradiction`) -- catching cases phrased
    too differently for lexical matching to find.

    Limitations: only compares each assistant message against the
    previous `CONTRADICTION_LOOKBACK` assistant messages, not the whole
    session, to bound the number of provider calls.
    """

    name = "semantic_contradiction"

    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        assistant_messages = [
            m for m in context.messages if m.role == MessageRole.ASSISTANT
        ]

        for i, later in enumerate(assistant_messages):
            window_start = max(0, i - CONTRADICTION_LOOKBACK)
            for earlier in assistant_messages[window_start:i]:
                same = self._provider.same_fact(earlier.content, later.content)
                if same.confidence < MIN_EMIT_CONFIDENCE or not same.same:
                    continue

                contradiction = self._provider.detect_semantic_contradiction(
                    earlier.content, later.content
                )
                if (
                    contradiction.confidence < MIN_EMIT_CONFIDENCE
                    or not contradiction.is_contradiction
                ):
                    continue

                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.CONTRADICTION,
                        severity=DetectionSeverity.MEDIUM,
                        confidence=round(contradiction.confidence, 3),
                        explanation=(
                            "Semantic analysis found the assistant's message at "
                            f"sequence {earlier.sequence_number} conflicts in "
                            f"meaning with its message at sequence "
                            f"{later.sequence_number}: {contradiction.explanation}"
                        ),
                        evidence=(
                            Evidence(
                                message_id=earlier.id,
                                excerpt=earlier.content[:_EXCERPT_LEN],
                                role="earlier_statement",
                            ),
                            Evidence(
                                message_id=later.id,
                                excerpt=later.content[:_EXCERPT_LEN],
                                role="later_statement",
                            ),
                        ),
                        related_message_ids=(earlier.id, later.id),
                        metadata={
                            "provider": contradiction.provider,
                            "model": contradiction.model,
                            "same_fact_confidence": same.confidence,
                        },
                    )
                )
        return signals


class SemanticInstructionDriftDetector:
    """Compares system/developer instructions against later assistant
    replies for meaning-level non-adherence.

    Complements the deterministic `InstructionDriftDetector`, which only
    catches literal, lexical violations of a small set of "never X" /
    "don't X" directive patterns. This detector instead asks the provider
    whether a reply fails to follow the instruction at all, in any form.

    Limitations: only considers `SYSTEM`/`DEVELOPER` messages as
    instructions (not general user requests, to bound cost and keep the
    comparison to messages that are unambiguously directives), and only
    checks the next `INSTRUCTION_LOOKAHEAD` assistant replies following
    each instruction.
    """

    name = "semantic_instruction_drift"

    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        instructions = [m for m in context.messages if m.role in _INSTRUCTION_ROLES]

        for instruction in instructions:
            later_assistant_messages = [
                m
                for m in context.messages
                if m.role == MessageRole.ASSISTANT
                and m.sequence_number > instruction.sequence_number
            ][:INSTRUCTION_LOOKAHEAD]

            for reply in later_assistant_messages:
                result = self._provider.detect_instruction_drift(
                    instruction.content, reply.content
                )
                if result.confidence < MIN_EMIT_CONFIDENCE or not result.drifted:
                    continue

                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.INSTRUCTION_DRIFT,
                        severity=DetectionSeverity.MEDIUM,
                        confidence=round(result.confidence, 3),
                        explanation=(
                            "Semantic analysis found the assistant's reply at "
                            f"sequence {reply.sequence_number} does not follow "
                            f"the instruction given at sequence "
                            f"{instruction.sequence_number}: {result.explanation}"
                        ),
                        evidence=(
                            Evidence(
                                message_id=instruction.id,
                                excerpt=instruction.content[:_EXCERPT_LEN],
                                role="instruction",
                            ),
                            Evidence(
                                message_id=reply.id,
                                excerpt=reply.content[:_EXCERPT_LEN],
                                role="violation",
                            ),
                        ),
                        related_message_ids=(instruction.id, reply.id),
                        metadata={
                            "provider": result.provider,
                            "model": result.model,
                        },
                    )
                )
        return signals


class SemanticRelevanceDetector:
    """Compares each user message against the assistant's immediate next
    reply for topical relevance, beyond word-overlap heuristics.

    Complements the deterministic `TopicDriftDetector`'s content-word
    Jaccard similarity, which cannot recognize a relevant reply that
    happens to use different vocabulary, nor an irrelevant reply that
    happens to reuse the user's words.

    Limitations: only compares a user message to the single next
    assistant reply, not the broader conversational arc.
    """

    name = "semantic_relevance"

    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        messages = context.messages

        for i, message in enumerate(messages):
            if message.role != MessageRole.USER:
                continue
            reply = next(
                (m for m in messages[i + 1 :] if m.role == MessageRole.ASSISTANT),
                None,
            )
            if reply is None:
                continue

            result = self._provider.assess_relevance(message.content, reply.content)
            if result.confidence < MIN_EMIT_CONFIDENCE or result.is_relevant:
                continue

            signals.append(
                Signal(
                    detector_name=self.name,
                    detection_type=DetectionType.TOPIC_DRIFT,
                    severity=DetectionSeverity.LOW,
                    confidence=round(result.confidence, 3),
                    explanation=(
                        "Semantic analysis found the assistant's reply at "
                        f"sequence {reply.sequence_number} is not relevant to "
                        f"the request at sequence {message.sequence_number}: "
                        f"{result.explanation}"
                    ),
                    evidence=(
                        Evidence(
                            message_id=message.id,
                            excerpt=message.content[:_EXCERPT_LEN],
                            role="task",
                        ),
                        Evidence(
                            message_id=reply.id,
                            excerpt=reply.content[:_EXCERPT_LEN],
                            role="response",
                        ),
                    ),
                    related_message_ids=(message.id, reply.id),
                    metadata={
                        "provider": result.provider,
                        "model": result.model,
                    },
                )
            )
        return signals


_CLASSIFICATION_SEVERITY = {
    EvidenceClassification.HIGH_CONFIDENCE_HALLUCINATION: DetectionSeverity.CRITICAL,
    EvidenceClassification.CONTRADICTED: DetectionSeverity.HIGH,
    EvidenceClassification.POSSIBLE_HALLUCINATION: DetectionSeverity.MEDIUM,
    EvidenceClassification.UNSUPPORTED: DetectionSeverity.LOW,
}

# Classifications worth surfacing as a `DetectionEvent`. SUPPORTED and
# INSUFFICIENT_EVIDENCE are not signals of a problem, so they are computed
# (for completeness/observability) but never emitted.
_EMIT_CLASSIFICATIONS = frozenset(_CLASSIFICATION_SEVERITY)


class ClaimSupportDetector:
    """Runs the evidence-based hallucination-risk pipeline
    (`app.analysis.semantic.hallucination.assess_hallucination_risk`) for
    each assistant message, using nearby tool-result output as the
    evidence pool.

    Only runs at all when the session contains at least one tool result;
    otherwise there is no evidence to check claims against, and the
    pipeline's own "no evidence" short-circuit would produce nothing but
    uninteresting `INSUFFICIENT_EVIDENCE` results for every message.

    Only SUPPORTED and INSUFFICIENT_EVIDENCE assessments are 'no news'
    and never emitted; CONTRADICTED / UNSUPPORTED / POSSIBLE_HALLUCINATION
    / HIGH_CONFIDENCE_HALLUCINATION are all surfaced, at severities that
    scale with how strong the evidence against the claim is.

    Limitations: evidence pool is bounded to tool results attached to
    messages within the previous `CLAIM_SUPPORT_LOOKBACK_MESSAGES`
    messages, not the whole session, to bound provider-call cost and
    prompt size.
    """

    name = "claim_support"

    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def detect(self, context: SessionContext) -> list[Signal]:
        messages = context.messages
        if not any(tc.result is not None for m in messages for tc in m.tool_calls):
            return []

        signals: list[Signal] = []
        for i, message in enumerate(messages):
            if message.role != MessageRole.ASSISTANT:
                continue

            window_start = max(0, i - CLAIM_SUPPORT_LOOKBACK_MESSAGES)
            evidence = tuple(
                str(tc.result.output)
                for m in messages[window_start:i]
                for tc in m.tool_calls
                if tc.result is not None and not tc.result.is_error
            )
            if not evidence:
                continue

            assessment = assess_hallucination_risk(
                self._provider, message.content, evidence
            )
            if assessment.classification not in _EMIT_CLASSIFICATIONS:
                continue

            signals.append(
                Signal(
                    detector_name=self.name,
                    detection_type=DetectionType.UNSUPPORTED_CLAIM,
                    severity=_CLASSIFICATION_SEVERITY[assessment.classification],
                    confidence=round(assessment.confidence, 3),
                    explanation=(
                        f"Evidence-based analysis of the assistant's message at "
                        f"sequence {message.sequence_number} against "
                        f"{len(evidence)} nearby tool result(s) yielded "
                        f"classification '{assessment.classification.value}': "
                        f"{assessment.explanation} This classification is "
                        "probabilistic unless independently verified."
                    ),
                    evidence=tuple(
                        Evidence(
                            message_id=message.id,
                            excerpt=fa.fact_text[:_EXCERPT_LEN],
                            role="extracted_fact",
                        )
                        for fa in assessment.fact_assessments
                    ),
                    related_message_ids=(message.id,),
                    metadata={
                        "classification": assessment.classification.value,
                        "fact_count": len(assessment.fact_assessments),
                    },
                )
            )
        return signals


def semantic_detectors(provider: AnalysisProvider) -> list[Detector]:
    """The standard set of semantic detectors, wired to one provider.

    Always safe to include regardless of whether a real LLM is
    configured: with `UnavailableAnalysisProvider`, every provider call
    returns confidence 0.0, which is below `MIN_EMIT_CONFIDENCE` for every
    detector above, so nothing is ever emitted.
    """
    return [
        SemanticContradictionDetector(provider),
        SemanticInstructionDriftDetector(provider),
        SemanticRelevanceDetector(provider),
        ClaimSupportDetector(provider),
    ]
