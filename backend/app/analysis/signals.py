"""The unit of output produced by every detector.

A `Signal` is a hypothesis, not a verdict. It always carries its own
confidence and the concrete evidence (source messages/tool calls/tool
results) it was derived from, so a human or a downstream process can
independently judge whether to trust it. Detectors must never claim
certainty they do not have -- see each detector module's docstring for how
its confidence is computed and what its known false-positive modes are.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.models import DetectionSeverity, DetectionType


@dataclass(frozen=True)
class Evidence:
    """A single piece of supporting evidence for a signal.

    `role` describes what part this evidence plays in the signal's
    explanation (e.g. "earlier_statement", "later_statement",
    "instruction", "violation") -- it maps directly onto
    `DetectionEvidence.evidence_role` when persisted.
    """

    message_id: str | None = None
    tool_call_id: str | None = None
    tool_result_id: str | None = None
    excerpt: str | None = None
    role: str = "supporting"


@dataclass(frozen=True)
class Signal:
    """A single detection produced by one detector.

    `confidence` is always in [0, 1] and is never treated as a probability
    of "hallucination" or "truth" -- it is the detector's own confidence
    that the *pattern it looks for* is present. Interpreting a signal
    (e.g. deciding whether a contradiction indicates a hallucination)
    requires additional evidence which may not exist yet; see each
    detector's `metadata` for fields like `external_verification_available`.
    """

    detector_name: str
    detection_type: DetectionType
    severity: DetectionSeverity
    confidence: float
    explanation: str
    evidence: tuple[Evidence, ...] = ()
    related_message_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be within [0, 1], got {self.confidence!r}"
            )
