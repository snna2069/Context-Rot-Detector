from app.analysis.detectors.behavior_shift import BehaviorShiftDetector
from app.analysis.detectors.context_growth import ContextGrowthDetector
from app.analysis.detectors.contradiction import ContradictionDetector
from app.analysis.detectors.fact_loss import FactLossDetector
from app.analysis.detectors.instruction_drift import InstructionDriftDetector
from app.analysis.detectors.omission import OmissionDetector
from app.analysis.detectors.repetition import RepetitionDetector
from app.analysis.detectors.stale_context import StaleContextDetector
from app.analysis.detectors.tool_result_neglect import ToolResultNeglectDetector
from app.analysis.detectors.topic_drift import TopicDriftDetector

__all__ = [
    "BehaviorShiftDetector",
    "ContextGrowthDetector",
    "ContradictionDetector",
    "FactLossDetector",
    "InstructionDriftDetector",
    "OmissionDetector",
    "RepetitionDetector",
    "StaleContextDetector",
    "ToolResultNeglectDetector",
    "TopicDriftDetector",
]


def default_detectors() -> list:
    """The standard set of deterministic detectors run by the engine.

    Each entry is independently testable and can be added/removed/reordered
    without affecting the others -- there is deliberately no single
    monolithic `detect_context_rot()` function.
    """
    return [
        ContextGrowthDetector(),
        RepetitionDetector(),
        OmissionDetector(),
        InstructionDriftDetector(),
        ContradictionDetector(),
        StaleContextDetector(),
        ToolResultNeglectDetector(),
        TopicDriftDetector(),
        BehaviorShiftDetector(),
        FactLossDetector(),
    ]
