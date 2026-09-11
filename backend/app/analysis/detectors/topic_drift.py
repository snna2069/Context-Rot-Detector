"""Topic / relevance-degradation detector.

What it measures
-----------------
How much the vocabulary used in a block of recent messages overlaps with
the immediately preceding block, using non-overlapping sliding windows of
content words (stopwords removed).

Why it matters
-----------------
A session that has drifted far from its recent topic without an explicit
topic change may indicate the agent lost track of the task, or is
responding to context that has become irrelevant to what is currently
being discussed.

Required inputs
-----------------
Ordered messages with `content`. Needs at least two full windows of
`WINDOW_SIZE` messages.

Limitations
-----------------
- Purely lexical (Jaccard similarity over content-word sets); no topic
  modeling or embeddings, so a legitimate topic change requested by the
  user is indistinguishable from unintentional drift.
- Sensitive to window size: very short windows are noisy, very long
  windows smooth out real drift.
- Only compares each window to the one immediately before it, so a slow,
  gradual drift across many windows may not cross the threshold at any
  single step even though the cumulative drift is large.

False positives
-----------------
- A user deliberately changing the subject mid-session ("actually, let's
  talk about something else") will also trigger this signal.

Confidence calculation
-----------------
`confidence` = `1 - similarity`, only reported when `similarity` is below
`DRIFT_SIMILARITY_THRESHOLD` and both windows have enough vocabulary
(`MIN_WINDOW_WORDS`) to make the comparison meaningful.
"""

from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.text_utils import content_words, jaccard_similarity
from app.models import DetectionSeverity, DetectionType

WINDOW_SIZE = 4
MIN_WINDOW_WORDS = 6
DRIFT_SIMILARITY_THRESHOLD = 0.12


class TopicDriftDetector:
    name = "topic_drift"

    def detect(self, context: SessionContext) -> list[Signal]:
        messages = context.messages
        if len(messages) < WINDOW_SIZE * 2:
            return []

        windows = [
            messages[i : i + WINDOW_SIZE]
            for i in range(0, len(messages) - WINDOW_SIZE + 1, WINDOW_SIZE)
        ]
        if len(windows) < 2:
            return []

        signals: list[Signal] = []
        previous_words: set[str] | None = None
        previous_window = None

        for window in windows:
            words: set[str] = set()
            for m in window:
                words |= content_words(m.content)

            if (
                previous_words is not None
                and previous_window is not None
                and len(previous_words) >= MIN_WINDOW_WORDS
                and len(words) >= MIN_WINDOW_WORDS
            ):
                similarity = jaccard_similarity(previous_words, words)
                if similarity < DRIFT_SIMILARITY_THRESHOLD:
                    confidence = round(min(1.0, 1 - similarity), 3)
                    signals.append(
                        Signal(
                            detector_name=self.name,
                            detection_type=DetectionType.TOPIC_DRIFT,
                            severity=DetectionSeverity.LOW,
                            confidence=confidence,
                            explanation=(
                                "Vocabulary overlap between messages "
                                f"{previous_window[0].sequence_number}-"
                                f"{previous_window[-1].sequence_number} and "
                                f"{window[0].sequence_number}-"
                                f"{window[-1].sequence_number} dropped to "
                                f"{similarity:.0%}, suggesting a topic shift."
                            ),
                            evidence=tuple(
                                Evidence(message_id=m.id, role="window") for m in window
                            ),
                            related_message_ids=tuple(m.id for m in window),
                            metadata={"similarity": similarity},
                        )
                    )
            previous_words = words
            previous_window = window
        return signals
