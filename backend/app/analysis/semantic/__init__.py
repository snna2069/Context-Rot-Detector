"""Semantic (LLM-backed) context-rot analysis.

Parallel to `app.analysis.detectors` (the purely deterministic detectors),
but every detector here is constructor-injected with an
`app.services.llm.provider.AnalysisProvider` instead of being
parameterless. They still conform to the same `app.analysis.base.Detector`
protocol, so `AnalysisEngine` needs no changes to run them.

Use `semantic_detectors(provider)` to build the standard set.
"""

from __future__ import annotations

from app.analysis.semantic.detectors import (
    ClaimSupportDetector,
    SemanticContradictionDetector,
    SemanticInstructionDriftDetector,
    SemanticRelevanceDetector,
    semantic_detectors,
)
from app.analysis.semantic.hallucination import (
    FactAssessment,
    HallucinationAssessment,
    assess_hallucination_risk,
)

__all__ = [
    "ClaimSupportDetector",
    "FactAssessment",
    "HallucinationAssessment",
    "SemanticContradictionDetector",
    "SemanticInstructionDriftDetector",
    "SemanticRelevanceDetector",
    "assess_hallucination_risk",
    "semantic_detectors",
]
