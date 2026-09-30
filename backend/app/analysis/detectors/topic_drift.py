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
- Measured against the session's accumulated vocabulary, so a session
  that drifts steadily from its very first turn (never establishing a
  baseline topic) is harder to flag than one that drifts away from an
  established subject.

False positives
-----------------
- A user deliberately changing the subject mid-session ("actually, let's
  talk about something else") will also trigger this signal.

Why the comparison is cumulative
-----------------
An earlier version compared each window only against the one immediately
before it. That measured "did the vocabulary change since the last few
messages?", which is true of essentially every productive conversation as
it moves through sub-topics -- so the detector fired on healthy sessions
at near-maximum confidence. Measured against the labeled corpus it had
12.5% precision and a 37% false-positive rate (see `evaluation/`).

Comparing against the union of everything said earlier instead asks a
different and much more relevant question: "has this block of messages
left the topic the session actually established?" Returning to an earlier
theme, or elaborating on it with new words, keeps a healthy overlap;
genuinely wandering off does not.

Confidence calculation
-----------------
Reported only when cumulative overlap falls below
`DRIFT_SIMILARITY_THRESHOLD`. Confidence scales with how far below the
threshold the overlap sits, capped at `MAX_CONFIDENCE`. It is *not* a
probability that the session is degraded -- a deliberate topic change
produces the same measurement as unintentional drift.
"""

from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.text_utils import containment_ratio, content_words
from app.models import DetectionSeverity, DetectionType

WINDOW_SIZE = 4
MIN_WINDOW_WORDS = 6
# Fraction of a window's content words that must already appear in the
# session's established vocabulary. Below this, the block is mostly
# talking about something the session has not been talking about.
MIN_CONTINUITY_RATIO = 0.2
MAX_CONFIDENCE = 0.6


class TopicDriftDetector:
    name = "topic_drift"
    detection_types = frozenset({DetectionType.TOPIC_DRIFT})

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
        # Vocabulary established by every window seen so far, not just the
        # previous one -- see the module docstring for why.
        established_words: set[str] = set()
        established_from = messages[0]

        for index, window in enumerate(windows):
            words: set[str] = set()
            for m in window:
                words |= content_words(m.content)

            if (
                index > 0
                and len(established_words) >= MIN_WINDOW_WORDS
                and len(words) >= MIN_WINDOW_WORDS
            ):
                similarity = containment_ratio(words, established_words)
                if similarity < MIN_CONTINUITY_RATIO:
                    shortfall = (
                        MIN_CONTINUITY_RATIO - similarity
                    ) / MIN_CONTINUITY_RATIO
                    confidence = round(
                        min(MAX_CONFIDENCE, MAX_CONFIDENCE * shortfall), 3
                    )
                    signals.append(
                        Signal(
                            detector_name=self.name,
                            detection_type=DetectionType.TOPIC_DRIFT,
                            severity=DetectionSeverity.LOW,
                            confidence=confidence,
                            explanation=(
                                "Vocabulary overlap between messages "
                                f"{established_from.sequence_number}-"
                                f"{windows[index - 1][-1].sequence_number} and "
                                f"{window[0].sequence_number}-"
                                f"{window[-1].sequence_number} dropped to "
                                f"{similarity:.0%} of the topic established so "
                                "far, suggesting a topic shift. A deliberate "
                                "change of subject looks the same as "
                                "unintentional drift to this detector."
                            ),
                            evidence=tuple(
                                Evidence(message_id=m.id, role="window") for m in window
                            ),
                            related_message_ids=tuple(m.id for m in window),
                            metadata={
                                "similarity": similarity,
                                "compared_against": "session_vocabulary",
                            },
                        )
                    )
            established_words |= words
        return signals
