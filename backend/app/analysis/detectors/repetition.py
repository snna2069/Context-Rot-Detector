"""Message repetition detector.

What it measures
-----------------
Near-duplicate messages from the same role appearing more than once in a
session (the agent -- or the user -- repeating itself almost verbatim).

Why it matters
-----------------
Repeated messages from the assistant often indicate the agent has lost
track of what it already said (a symptom of context rot) rather than a
deliberate design choice. Repeated user messages can indicate the user
had to re-state something the agent failed to act on.

Required inputs
-----------------
Ordered messages with `role` and `content`.

Limitations
-----------------
- Uses character-level similarity (`difflib.SequenceMatcher`), which is
  sensitive to superficial rewording; it will miss paraphrased repetition
  that a semantic/embedding-based comparison would catch (a natural
  future upgrade, not implemented here to keep this signal deterministic).
- Compares only within a bounded look-back window for performance, so
  repetition across very distant turns may be missed.

False positives
-----------------
- Short, generic messages (e.g. "Understood." or "Yes.") are naturally
  similar without being a meaningful repetition signal; a minimum content
  length is enforced to reduce this.

Confidence calculation
-----------------
`confidence` = similarity ratio (0..1) between the two messages, only
reported when the ratio exceeds `SIMILARITY_THRESHOLD`.
"""

from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.text_utils import text_similarity_ratio
from app.models import DetectionSeverity, DetectionType

SIMILARITY_THRESHOLD = 0.85
MIN_CONTENT_LENGTH = 20
LOOKBACK_WINDOW = 20


class RepetitionDetector:
    name = "repetition"

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        messages = context.messages

        for i, message in enumerate(messages):
            if len(message.content) < MIN_CONTENT_LENGTH:
                continue
            window_start = max(0, i - LOOKBACK_WINDOW)
            for prior in messages[window_start:i]:
                if prior.role != message.role:
                    continue
                if len(prior.content) < MIN_CONTENT_LENGTH:
                    continue
                ratio = text_similarity_ratio(prior.content, message.content)
                if ratio < SIMILARITY_THRESHOLD:
                    continue

                severity = (
                    DetectionSeverity.MEDIUM if ratio >= 0.95 else DetectionSeverity.LOW
                )
                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.REPETITION,
                        severity=severity,
                        confidence=round(ratio, 3),
                        explanation=(
                            f"Message at sequence {message.sequence_number} is "
                            f"{ratio:.0%} similar to an earlier {message.role} "
                            f"message at sequence {prior.sequence_number}."
                        ),
                        evidence=(
                            Evidence(
                                message_id=prior.id,
                                excerpt=prior.content[:200],
                                role="prior_occurrence",
                            ),
                            Evidence(
                                message_id=message.id,
                                excerpt=message.content[:200],
                                role="repeated_occurrence",
                            ),
                        ),
                        related_message_ids=(prior.id, message.id),
                        metadata={"similarity_ratio": ratio},
                    )
                )
                break  # avoid cascading matches against multiple prior duplicates
        return signals
