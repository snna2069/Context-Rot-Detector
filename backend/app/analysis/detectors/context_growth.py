"""Context growth detector.

What it measures
-----------------
The rate at which session content size (character count, as a
dependency-free proxy for token count) is growing, specifically whether
the most recent portion of the session is growing much faster than the
session's own historical average.

Why it matters
-----------------
Context growth is *not itself* context rot -- a long session can be
perfectly healthy. But accelerating growth is a useful leading indicator
and a contributing input to the health score: it raises the likelihood
that other signals (repetition, staleness, omission) will start to
appear, and it is useful denominator information when interpreting them.

Required inputs
-----------------
Ordered messages with `content`. Needs at least `MIN_MESSAGES` messages;
short sessions are not analyzed since growth "rate" is meaningless there.

Limitations
-----------------
- Character count is a coarse proxy for token count.
- Uses a simple recent-window-vs-historical-average comparison; it does
  not model growth curves or detect exponential blow-up precisely.

False positives
-----------------
- A single unusually long message (e.g. a large pasted log or tool
  output) can trigger this without representing a genuine trend.

Confidence calculation
-----------------
Only emitted when `recent_avg / historical_avg` exceeds
`GROWTH_RATIO_THRESHOLD`; confidence scales linearly with how far past
the threshold the ratio is, capped at 1.0.
"""

from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.models import DetectionSeverity, DetectionType

MIN_MESSAGES = 12
RECENT_WINDOW = 6
GROWTH_RATIO_THRESHOLD = 2.0


class ContextGrowthDetector:
    name = "context_growth"

    def detect(self, context: SessionContext) -> list[Signal]:
        messages = context.messages
        if len(messages) < MIN_MESSAGES:
            return []

        lengths = [len(m.content) for m in messages]
        historical = lengths[:-RECENT_WINDOW]
        recent = lengths[-RECENT_WINDOW:]
        historical_avg = sum(historical) / len(historical)
        recent_avg = sum(recent) / len(recent)

        if historical_avg <= 0:
            return []

        ratio = recent_avg / historical_avg
        if ratio <= GROWTH_RATIO_THRESHOLD:
            return []

        confidence = min(1.0, (ratio - GROWTH_RATIO_THRESHOLD) / GROWTH_RATIO_THRESHOLD)
        recent_messages = messages[-RECENT_WINDOW:]
        return [
            Signal(
                detector_name=self.name,
                detection_type=DetectionType.CONTEXT_GROWTH,
                severity=DetectionSeverity.INFO,
                confidence=round(confidence, 3),
                explanation=(
                    f"Recent messages average {recent_avg:.0f} characters, "
                    f"{ratio:.1f}x the session's historical average of "
                    f"{historical_avg:.0f} characters."
                ),
                evidence=tuple(
                    Evidence(message_id=m.id, role="supporting")
                    for m in recent_messages
                ),
                related_message_ids=tuple(m.id for m in recent_messages),
                metadata={
                    "recent_avg_chars": recent_avg,
                    "historical_avg_chars": historical_avg,
                    "ratio": ratio,
                },
            )
        ]
