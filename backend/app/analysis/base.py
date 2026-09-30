"""Detector interface and the base contract every detector must satisfy."""

from __future__ import annotations

from typing import ClassVar, Protocol

from app.analysis.context import SessionContext
from app.analysis.signals import Signal
from app.models import DetectionType


class Detector(Protocol):
    """A single, independently-testable context-rot signal detector.

    Implementations must be pure functions of the `SessionContext`: no
    database access, no network calls, no LLM calls. This keeps every
    detector deterministic and reproducible, per the project's engineering
    rules. Detectors that need an LLM or external verification belong in a
    separate, explicitly-named service layered on top of this engine, not
    mixed into these deterministic detectors.

    `detection_types` declares every `DetectionType` this detector is
    capable of emitting. It is what lets the engine answer "which health
    dimensions did we actually manage to assess?" when a detector fails:
    a dimension covered only by a detector that raised must be reported
    as *not assessed* rather than as a perfect score. Declaring it on the
    detector keeps that mapping next to the code that emits the signals,
    so it cannot drift from reality.
    """

    name: str
    detection_types: ClassVar[frozenset[DetectionType]]

    def detect(self, context: SessionContext) -> list[Signal]: ...
