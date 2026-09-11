"""Fact loss detector.

What it measures
-----------------
Cases where the assistant previously stated a concrete value for a
subject, and later -- when the conversation continues to reference that
same subject -- responds with explicit hedging/uncertainty language
("I don't know", "I'm not sure", "I don't have that information") instead
of recalling the previously established value.

Why it matters
-----------------
This is one of the most direct, human-legible symptoms of context rot:
the agent had the information and later behaves as though it does not.

Required inputs
-----------------
Ordered messages with `role`, `content`.

Limitations
-----------------
- Relies on the same narrow subject/value regex extractor as the
  contradiction/stale-context detectors to establish "previously known"
  facts (only the *first* establishment of a subject is used, not the
  most recently updated value), so it inherits the same extraction blind
  spots.
- Hedging-language detection is a fixed phrase list; it will miss novel or
  indirect ways of expressing uncertainty and may flag legitimate
  uncertainty about a *different*, coincidentally similar subject.
- Requires the subject term to appear verbatim in the hedging message (or
  a preceding user question) to associate the hedge with a prior fact.

False positives
-----------------
- The assistant may use a hedging phrase for unrelated, genuine reasons
  that happen to mention the same subject term in a different sense.

Confidence calculation
-----------------
Base confidence of 0.55, +0.15 if a preceding user message (asked after
the fact was established but before the hedge) also mentions the subject
term -- a stronger link between the question and the previously
established fact -- capped at 0.8.
"""

from __future__ import annotations

import re

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.statements import extract_statements
from app.models import DetectionSeverity, DetectionType, MessageRole

_HEDGE_PHRASES = [
    "i don't know",
    "i do not know",
    "i'm not sure",
    "i am not sure",
    "no information about",
    "don't have that information",
    "do not have that information",
    "unable to recall",
    "not sure what",
    "unclear what",
]

MAX_CONFIDENCE = 0.8
BASE_CONFIDENCE = 0.55
STRONG_LINK_BONUS = 0.15


class FactLossDetector:
    name = "fact_loss"

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        established: dict[str, tuple] = {}

        for message in context.messages:
            if message.role != MessageRole.ASSISTANT:
                continue
            for statement in extract_statements(message.content):
                established.setdefault(statement.subject, (message, statement.value))

        if not established:
            return []

        for message in context.messages:
            if message.role != MessageRole.ASSISTANT:
                continue
            lowered = message.content.lower()
            hedge = next(
                (phrase for phrase in _HEDGE_PHRASES if phrase in lowered), None
            )
            if hedge is None:
                continue

            for subject, (established_message, value) in established.items():
                if established_message.sequence_number >= message.sequence_number:
                    continue
                subject_pattern = re.compile(
                    rf"\b{re.escape(subject)}\b", re.IGNORECASE
                )
                if not subject_pattern.search(lowered):
                    continue

                confidence = BASE_CONFIDENCE
                preceding_user_messages = [
                    m
                    for m in context.messages
                    if m.role == MessageRole.USER
                    and established_message.sequence_number
                    < m.sequence_number
                    < message.sequence_number
                ]
                if any(
                    subject_pattern.search(m.content.lower())
                    for m in preceding_user_messages
                ):
                    confidence += STRONG_LINK_BONUS
                confidence = min(MAX_CONFIDENCE, round(confidence, 3))

                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.FACT_LOSS,
                        severity=DetectionSeverity.HIGH,
                        confidence=confidence,
                        explanation=(
                            f"'{subject}' was established as '{value}' at sequence "
                            f"{established_message.sequence_number}, but the "
                            f"assistant expressed uncertainty about '{subject}' at "
                            f"sequence {message.sequence_number} ('{hedge}')."
                        ),
                        evidence=(
                            Evidence(
                                message_id=established_message.id,
                                excerpt=established_message.content[:200],
                                role="established_fact",
                            ),
                            Evidence(
                                message_id=message.id,
                                excerpt=message.content[:200],
                                role="hedge_response",
                            ),
                        ),
                        related_message_ids=(established_message.id, message.id),
                        metadata={
                            "subject": subject,
                            "established_value": value,
                            "hedge_phrase": hedge,
                        },
                    )
                )
        return signals
