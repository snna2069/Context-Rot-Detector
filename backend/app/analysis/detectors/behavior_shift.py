"""Sudden agent behavior shift detector.

What it measures
-----------------
Abrupt changes in observable assistant behavior: a sudden, large jump in
response length compared to the session's own recent baseline.

Why it matters
-----------------
A sharp behavioral discontinuity (e.g. a normally terse assistant
suddenly producing a very long response, or vice versa) is often a
visible symptom of underlying context rot, even before any specific
factual error can be pinned down.

Required inputs
-----------------
Ordered assistant messages with `content`.

Limitations
-----------------
- Uses a simple statistical threshold (rolling mean/stddev of message
  length in characters) rather than any semantic understanding of
  "behavior."
- Requires a minimum history to establish a meaningful baseline; sessions
  with `MIN_HISTORY` or fewer assistant messages are not analyzed.
- A legitimate reason for the shift (e.g. the user asked for a much more
  detailed answer) is indistinguishable from an unintended one.

False positives
-----------------
- A single message that is unusually long or short for a good reason
  (e.g. the user pasted a large document to summarize) will be flagged.

Confidence calculation
-----------------
Confidence scales with how many standard deviations the message length
deviates from the rolling baseline, capped at `MAX_CONFIDENCE`, since this
signal is purely statistical and does not identify *why* behavior
changed.
"""

from __future__ import annotations

import statistics

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.models import DetectionSeverity, DetectionType, MessageRole

MIN_HISTORY = 6
Z_SCORE_THRESHOLD = 2.5
MAX_CONFIDENCE = 0.75


class BehaviorShiftDetector:
    name = "behavior_shift"

    def detect(self, context: SessionContext) -> list[Signal]:
        assistant_messages = [
            m for m in context.messages if m.role == MessageRole.ASSISTANT
        ]
        if len(assistant_messages) <= MIN_HISTORY:
            return []

        signals: list[Signal] = []
        lengths = [len(m.content) for m in assistant_messages]

        for i in range(MIN_HISTORY, len(assistant_messages)):
            baseline = lengths[:i]
            mean = statistics.fmean(baseline)
            stdev = statistics.pstdev(baseline)
            if stdev == 0:
                continue

            z_score = (lengths[i] - mean) / stdev
            if abs(z_score) < Z_SCORE_THRESHOLD:
                continue

            confidence = min(
                MAX_CONFIDENCE, round(abs(z_score) / (Z_SCORE_THRESHOLD * 2), 3)
            )
            message = assistant_messages[i]
            direction = "longer" if z_score > 0 else "shorter"
            signals.append(
                Signal(
                    detector_name=self.name,
                    detection_type=DetectionType.BEHAVIOR_SHIFT,
                    severity=DetectionSeverity.LOW,
                    confidence=confidence,
                    explanation=(
                        f"Assistant message at sequence {message.sequence_number} "
                        f"is {direction} ({len(message.content)} chars) than its "
                        f"recent baseline ({mean:.0f} +/- {stdev:.0f} chars), a "
                        f"{z_score:.1f} standard-deviation shift."
                    ),
                    evidence=(
                        Evidence(
                            message_id=message.id,
                            excerpt=message.content[:200],
                            role="deviating_message",
                        ),
                    ),
                    related_message_ids=(message.id,),
                    metadata={
                        "z_score": z_score,
                        "baseline_mean": mean,
                        "baseline_stdev": stdev,
                    },
                )
            )
        return signals
