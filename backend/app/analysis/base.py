"""Detector interface and the base contract every detector must satisfy."""

from __future__ import annotations

from typing import Protocol

from app.analysis.context import SessionContext
from app.analysis.signals import Signal


class Detector(Protocol):
    """A single, independently-testable context-rot signal detector.

    Implementations must be pure functions of the `SessionContext`: no
    database access, no network calls, no LLM calls. This keeps every
    detector deterministic and reproducible, per the project's engineering
    rules. Detectors that need an LLM or external verification belong in a
    separate, explicitly-named service layered on top of this engine, not
    mixed into these deterministic detectors.
    """

    name: str

    def detect(self, context: SessionContext) -> list[Signal]: ...
