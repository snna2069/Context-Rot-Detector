"""Contradiction detector.

What it measures
-----------------
Simple declarative statements made by the assistant ("the deadline is
March 15th") that are later re-stated with a materially different value
for the same subject ("the deadline is April 1st").

Why it matters
-----------------
Restating a previously given fact with a different value is one of the
clearest, cheapest-to-compute forms of internal inconsistency in a long
session, and a leading indicator of context rot.

IMPORTANT: a detected contradiction is evidence of inconsistency, not
proof of hallucination. This detector never labels either statement as
"true" or "false" -- it only reports that two statements conflict, along
with whether any tool result exists in the session that could be used to
verify either one (`metadata["external_verification_available"]`).

Required inputs
-----------------
Ordered messages with `role`, `content`; optionally tool call/result data
(used only to set `external_verification_available`).

Limitations
-----------------
- Statement extraction (`app.analysis.statements`) uses a narrow regex
  grammar for "<subject> is/are/was/were <value>" style clauses. It has no
  coreference resolution, no synonym handling, and will both over- and
  under-extract compared to a true NLP/LLM-based extractor.
- Only compares statements with an identical (normalized) subject string;
  "the deadline" and "our deadline" are treated as different subjects.
- Cannot judge whether a later statement is a legitimate update/correction
  versus an unintentional contradiction.

False positives
-----------------
- Legitimate updates ("the deadline moved to April 1st because...") are
  indistinguishable from accidental contradictions at this lexical level.
- Minor rephrasing of the same value (e.g. "5" vs "five") may be flagged
  as conflicting since no numeric/unit normalization is performed.

Confidence calculation
-----------------
Base confidence of 0.5 (subjects matched exactly, which already rules out
some coreference risk). Confidence increases with how lexically different
the two values are (1 - character similarity ratio), capped at 0.85 --
contradictions are never reported above 0.85 confidence by this purely
lexical detector, deliberately leaving room for higher-confidence
verification by future evidence-based analysis.
"""

from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.statements import extract_statements
from app.analysis.text_utils import text_similarity_ratio
from app.models import DetectionSeverity, DetectionType, MessageRole

VALUE_DIFFERENCE_THRESHOLD = 0.6
MAX_CONFIDENCE = 0.85


class ContradictionDetector:
    name = "contradiction"

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        assistant_messages = [
            m for m in context.messages if m.role == MessageRole.ASSISTANT
        ]
        has_tool_results = any(
            tc.result is not None for m in context.messages for tc in m.tool_calls
        )

        statements_by_subject: dict[str, list] = {}
        for message in assistant_messages:
            for statement in extract_statements(message.content):
                statements_by_subject.setdefault(statement.subject, []).append(
                    (message, statement.value)
                )

        for subject, occurrences in statements_by_subject.items():
            if len(occurrences) < 2:
                continue
            for i in range(1, len(occurrences)):
                earlier_message, earlier_value = occurrences[i - 1]
                later_message, later_value = occurrences[i]
                similarity = text_similarity_ratio(earlier_value, later_value)
                difference = 1 - similarity
                if difference < VALUE_DIFFERENCE_THRESHOLD:
                    continue

                confidence = min(MAX_CONFIDENCE, round(0.5 + 0.35 * difference, 3))
                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.CONTRADICTION,
                        severity=DetectionSeverity.MEDIUM,
                        confidence=confidence,
                        explanation=(
                            f"Assistant stated '{subject} is {earlier_value}' at "
                            f"sequence {earlier_message.sequence_number}, then "
                            f"'{subject} is {later_value}' at sequence "
                            f"{later_message.sequence_number}. This is evidence of "
                            "inconsistency, not confirmed proof that either "
                            "statement is a hallucination."
                        ),
                        evidence=(
                            Evidence(
                                message_id=earlier_message.id,
                                excerpt=earlier_message.content[:200],
                                role="earlier_statement",
                            ),
                            Evidence(
                                message_id=later_message.id,
                                excerpt=later_message.content[:200],
                                role="later_statement",
                            ),
                        ),
                        related_message_ids=(earlier_message.id, later_message.id),
                        metadata={
                            "subject": subject,
                            "earlier_value": earlier_value,
                            "later_value": later_value,
                            "external_verification_available": has_tool_results,
                        },
                    )
                )
        return signals
