"""Instruction drift detector.

What it measures
-----------------
Explicit negative directives ("never mention X", "don't do Y") stated in
system/developer/user messages, and whether a later assistant message
appears to violate the literal directive.

Why it matters
-----------------
Long sessions increase the risk that earlier instructions get "crowded
out" by newer context. A literal violation of an explicit directive is a
strong, cheap-to-compute signal of instruction-adherence failure.

Required inputs
-----------------
Ordered messages with `role` and `content`.

Limitations
-----------------
- Directive extraction is regex-based over a small set of English
  imperative patterns ("never X", "don't/do not X"); it will miss
  directives phrased differently (e.g. "please avoid X", "X is off
  limits").
- Violation detection is purely lexical: does the forbidden term appear
  literally in a later assistant message. It has no synonym or semantic
  understanding, so a semantically-equivalent violation using different
  wording (e.g. "shrimp" for a "no shellfish" directive) is not caught.
- Very short forbidden terms are excluded to reduce noise.

False positives
-----------------
- A directive term appearing in a *negated* context in the later message
  (e.g. "I will not mention shellfish") is still literally matched; this
  detector cannot currently distinguish a negated mention from an actual
  violation, so confidence is deliberately capped at a moderate level.

Confidence calculation
-----------------
Base confidence of 0.6, +0.1 for each additional literal occurrence of
the forbidden term found in the same message (capped at 0.9), since
repeated occurrences make a coincidental/negated mention less likely.
"""

from __future__ import annotations

import re

from app.analysis.context import SessionContext
from app.analysis.signals import Evidence, Signal
from app.models import DetectionSeverity, DetectionType, MessageRole

_DIRECTIVE_PATTERNS = [
    re.compile(
        r"\bnever\s+(?:mention|suggest|say|recommend|use)\s+"
        r"(?P<term>[\w][\w \-']{2,40}?)(?:[.,!]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdo(?:n'?t| not)\s+(?:mention|suggest|say|recommend|use)\s+"
        r"(?P<term>[\w][\w \-']{2,40}?)(?:[.,!]|$)",
        re.IGNORECASE,
    ),
]

MIN_TERM_LENGTH = 3
DIRECTIVE_ROLES = {MessageRole.SYSTEM, MessageRole.DEVELOPER, MessageRole.USER}


class InstructionDriftDetector:
    name = "instruction_drift"

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        directives: list[tuple] = []

        for message in context.messages:
            if message.role not in DIRECTIVE_ROLES:
                continue
            for pattern in _DIRECTIVE_PATTERNS:
                for match in pattern.finditer(message.content):
                    term = match.group("term").strip().lower()
                    if len(term) >= MIN_TERM_LENGTH:
                        directives.append((message, term))

        for directive_message, term in directives:
            term_pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            for message in context.messages:
                if message.sequence_number <= directive_message.sequence_number:
                    continue
                if message.role != MessageRole.ASSISTANT:
                    continue
                occurrences = term_pattern.findall(message.content)
                if not occurrences:
                    continue

                confidence = min(0.9, 0.6 + 0.1 * (len(occurrences) - 1))
                signals.append(
                    Signal(
                        detector_name=self.name,
                        detection_type=DetectionType.INSTRUCTION_DRIFT,
                        severity=DetectionSeverity.MEDIUM,
                        confidence=round(confidence, 3),
                        explanation=(
                            f"A directive against '{term}' was stated at sequence "
                            f"{directive_message.sequence_number}, but the "
                            f"assistant's message at sequence "
                            f"{message.sequence_number} contains '{term}'."
                        ),
                        evidence=(
                            Evidence(
                                message_id=directive_message.id,
                                excerpt=directive_message.content[:200],
                                role="instruction",
                            ),
                            Evidence(
                                message_id=message.id,
                                excerpt=message.content[:200],
                                role="violation",
                            ),
                        ),
                        related_message_ids=(directive_message.id, message.id),
                        metadata={"forbidden_term": term},
                    )
                )
        return signals
