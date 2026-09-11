"""Stale context detector.

What it measures
-----------------
Facts/statements established earlier in the session (via the shared
statement extractor in `app.analysis.statements`) that have not been
reaffirmed, updated, or referenced again within a configurable number of
subsequent assistant turns.

Why it matters
-----------------
A long-running session accumulates state. Information that was true when
stated may need to be re-verified before being relied upon much later --
flagging it lets a human or downstream process decide whether to
re-confirm it, rather than silently assuming it still holds.

Required inputs
-----------------
Ordered assistant messages with `content`.

Limitations
-----------------
- Uses the same narrow subject/value regex extractor as the contradiction
  detector; it will miss statements phrased differently and cannot judge
  whether a fact needs re-verification versus being timeless (e.g. "the
  sky is blue" is treated the same as "the deadline is Friday").
- "Staleness" here is purely a function of turn distance, not real-world
  time or topic relevance.

False positives
-----------------
- Facts that genuinely never need to change (e.g. a project's name) will
  still be flagged once the turn-distance threshold is crossed.

Confidence calculation
-----------------
Confidence scales linearly with how far past the staleness threshold the
last reference is, capped at `MAX_CONFIDENCE` (this is an informational
signal about information age, not a claim that the fact is wrong).
"""

from __future__ import annotations

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.analysis.statements import extract_statements
from app.models import DetectionSeverity, DetectionType, MessageRole

STALENESS_TURN_THRESHOLD = 10
MAX_CONFIDENCE = 0.7


class StaleContextDetector:
    name = "stale_context"

    def detect(self, context: SessionContext) -> list[Signal]:
        assistant_messages = [
            m for m in context.messages if m.role == MessageRole.ASSISTANT
        ]
        if len(assistant_messages) < STALENESS_TURN_THRESHOLD:
            return []

        last_mentioned: dict[str, tuple] = {}
        for message in assistant_messages:
            for statement in extract_statements(message.content):
                last_mentioned[statement.subject] = (message, statement.value)

        latest_turn = assistant_messages[-1].sequence_number
        signals: list[Signal] = []
        for subject, (message, value) in last_mentioned.items():
            turns_since = latest_turn - message.sequence_number
            if turns_since < STALENESS_TURN_THRESHOLD:
                continue

            confidence = min(
                MAX_CONFIDENCE,
                MAX_CONFIDENCE * (turns_since / (STALENESS_TURN_THRESHOLD * 2)),
            )
            signals.append(
                Signal(
                    detector_name=self.name,
                    detection_type=DetectionType.STALE_CONTEXT,
                    severity=DetectionSeverity.LOW,
                    confidence=round(confidence, 3),
                    explanation=(
                        f"'{subject} is {value}' was last stated at sequence "
                        f"{message.sequence_number}, {turns_since} assistant "
                        "turns ago, and has not been reaffirmed since."
                    ),
                    evidence=(
                        Evidence(
                            message_id=message.id,
                            excerpt=message.content[:200],
                            role="last_reference",
                        ),
                    ),
                    related_message_ids=(message.id,),
                    metadata={
                        "subject": subject,
                        "value": value,
                        "turns_since": turns_since,
                    },
                )
            )
        return signals
