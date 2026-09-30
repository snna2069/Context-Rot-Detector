"""Detection-quality evaluation (Phase 3).

Separate from `tests/` on purpose. The test suite answers "does the code
behave as written?"; this package answers a different and much harder
question: "does the detector suite actually identify context rot, and is
its confidence meaningful?"

Nothing here runs an LLM. The corpus is evaluated against the
deterministic detectors only, so a run is free, offline, reproducible,
and safe to execute in CI.

Read `corpus/README.md` before adding scenarios -- a corpus written to
make the detectors look good is worse than no corpus at all.
"""

from __future__ import annotations

from evaluation.harness import (
    CorpusScenario,
    DetectorMetrics,
    EvaluationReport,
    evaluate_corpus,
    load_corpus,
)

__all__ = [
    "CorpusScenario",
    "DetectorMetrics",
    "EvaluationReport",
    "evaluate_corpus",
    "load_corpus",
]
