"""Important-information omission detector.

What it measures
-----------------
Explicitly marked "important" statements (via marker phrases such as
"important", "critical", "must", "never", "always", "remember", "note:",
"required") made by the user, system, or developer, and whether a later
assistant reply that is clearly on the same topic (shares vocabulary with
the marked statement) fails to restate any of the statement's
distinguishing terms.

Why it matters
-----------------
Users/operators mark information as important precisely because it must
not be dropped from context. If a later, clearly-related reply omits all
of the distinguishing terms from that statement, it is a strong signal
the information was not actually used.

Required inputs
-----------------
Ordered messages with `role`, `content`.

Limitations
-----------------
- Requires an explicit marker phrase; important information stated
  without such a marker is invisible to this detector.
- "Same topic" is determined by shared content-word overlap with the
  follow-up question, not semantic similarity, so a related-but
  differently-worded follow-up (e.g. "seafood" vs. "shellfish") will not
  be linked and this detector will miss the omission.
- Cannot distinguish "the assistant correctly decided the constraint did
  not apply" from "the assistant forgot the constraint."

False positives
-----------------
- A follow-up on a similar surface topic that genuinely does not require
  repeating the marked information will still be flagged.

Confidence calculation
-----------------
Base confidence of 0.5, +0.2 if the follow-up question's topical overlap
with the marked statement is high (>= `STRONG_OVERLAP_THRESHOLD`), capped
at 0.7 (kept moderate because the detector cannot confirm the omission
was actually consequential).
"""

from __future__ import annotations

import re

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.text_utils import content_words, jaccard_similarity
from app.models import DetectionSeverity, DetectionType, MessageRole

_MARKER_PATTERN = re.compile(
    r"\b(important|critical|must|never|always|remember|note:|required)\b",
    re.IGNORECASE,
)
MARKER_ROLES = {MessageRole.USER, MessageRole.SYSTEM, MessageRole.DEVELOPER}
TOPIC_OVERLAP_THRESHOLD = 0.15
STRONG_OVERLAP_THRESHOLD = 0.3
LOOKAHEAD_MESSAGES = 10
BASE_CONFIDENCE = 0.5
STRONG_OVERLAP_BONUS = 0.2


class OmissionDetector:
    name = "omission"

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        messages = context.messages

        for i, marker_message in enumerate(messages):
            if marker_message.role not in MARKER_ROLES:
                continue
            if not _MARKER_PATTERN.search(marker_message.content):
                continue
            key_terms = content_words(marker_message.content)
            if not key_terms:
                continue

            for follow_up in messages[i + 1 : i + 1 + LOOKAHEAD_MESSAGES]:
                if follow_up.role != MessageRole.USER:
                    continue
                follow_up_words = content_words(follow_up.content)
                overlap = jaccard_similarity(key_terms, follow_up_words)
                if overlap < TOPIC_OVERLAP_THRESHOLD:
                    continue

                reply = next(
                    (
                        m
                        for m in messages
                        if m.sequence_number > follow_up.sequence_number
                        and m.role == MessageRole.ASSISTANT
                    ),
                    None,
                )
                if reply is None:
                    continue

                reply_words = content_words(reply.content)
                if key_terms & reply_words:
                    continue  # at least one distinguishing term was restated

                confidence = BASE_CONFIDENCE + (
                    STRONG_OVERLAP_BONUS if overlap >= STRONG_OVERLAP_THRESHOLD else 0.0
                )
                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.OMISSION,
                        severity=DetectionSeverity.MEDIUM,
                        confidence=round(confidence, 3),
                        explanation=(
                            "Important information marked at sequence "
                            f"{marker_message.sequence_number} was not restated in "
                            f"the assistant's reply at sequence "
                            f"{reply.sequence_number}, despite a related follow-up "
                            f"question at sequence {follow_up.sequence_number}."
                        ),
                        evidence=(
                            Evidence(
                                message_id=marker_message.id,
                                excerpt=marker_message.content[:200],
                                role="marked_statement",
                            ),
                            Evidence(
                                message_id=follow_up.id,
                                excerpt=follow_up.content[:200],
                                role="follow_up_question",
                            ),
                            Evidence(
                                message_id=reply.id,
                                excerpt=reply.content[:200],
                                role="reply_missing_information",
                            ),
                        ),
                        related_message_ids=(
                            marker_message.id,
                            follow_up.id,
                            reply.id,
                        ),
                        metadata={"topic_overlap": overlap},
                    )
                )
        return signals
