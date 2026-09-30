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
from app.analysis.text_utils import (
    extract_numbers,
    numeric_conflict,
    text_similarity_ratio,
)
from app.models import DetectionSeverity, DetectionType, MessageRole

VALUE_DIFFERENCE_THRESHOLD = 0.6
MAX_CONFIDENCE = 0.85
# Confidence used when two values disagree on a number. Numeric
# disagreement is a much stronger and less ambiguous signal than lexical
# dissimilarity, so it is scored above the lexical floor but still short
# of certainty -- the values may be describing different things the
# subject extractor conflated.
NUMERIC_CONFLICT_CONFIDENCE = 0.8


class ContradictionDetector:
    name = "contradiction"
    detection_types = frozenset({DetectionType.CONTRADICTION})

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

                # An update the user themselves supplied is not the agent
                # contradicting itself -- it is the agent correctly
                # incorporating new information. Flagging it would train
                # users to ignore the tool, so it is suppressed here.
                if self._user_supplied_value(
                    context, earlier_message, later_message, later_value
                ):
                    continue

                # Numeric disagreement is checked first and independently
                # of lexical similarity: two values can be textually
                # near-identical ("30 seconds" / "5 seconds") while
                # asserting incompatible facts.
                numbers_conflict = numeric_conflict(earlier_value, later_value)
                similarity = text_similarity_ratio(earlier_value, later_value)
                difference = 1 - similarity

                if numbers_conflict:
                    confidence = NUMERIC_CONFLICT_CONFIDENCE
                    basis = "numeric"
                elif numbers_conflict is False:
                    # Same numbers on both sides: the values agree on the
                    # only part that is precisely comparable, so lexical
                    # difference alone is not treated as a contradiction.
                    continue
                elif difference >= VALUE_DIFFERENCE_THRESHOLD:
                    confidence = min(MAX_CONFIDENCE, round(0.5 + 0.35 * difference, 3))
                    basis = "lexical"
                else:
                    continue
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
                            "comparison_basis": basis,
                            "external_verification_available": has_tool_results,
                        },
                    )
                )
        return signals

    @staticmethod
    def _user_supplied_value(
        context: SessionContext,
        earlier_message,
        later_message,
        later_value: str,
    ) -> bool:
        """Did a non-assistant turn introduce the new value in between?

        Deliberately conservative: it only suppresses when the *specific*
        new value (its numbers, or the value text itself) appears in a
        user/system/developer message positioned between the two
        assistant statements. That is strong evidence the change was
        instructed rather than invented.
        """
        authored_roles = {
            MessageRole.USER,
            MessageRole.SYSTEM,
            MessageRole.DEVELOPER,
        }
        later_numbers = set(extract_numbers(later_value))
        normalized_value = later_value.strip().lower()

        for message in context.messages:
            if not (
                earlier_message.sequence_number
                < message.sequence_number
                < later_message.sequence_number
            ):
                continue
            if message.role not in authored_roles:
                continue
            content = message.content.lower()
            if later_numbers and later_numbers <= set(extract_numbers(content)):
                return True
            if len(normalized_value) > 2 and normalized_value in content:
                return True
        return False
