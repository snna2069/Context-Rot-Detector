"""Corpus loading, detector execution, and metric computation.

Metric definitions used throughout (per detection type, over scenarios):

* TP -- the type was expected for a scenario and at least one signal of
  that type was emitted.
* FP -- the type was emitted for a scenario where it was not expected.
* FN -- the type was expected but nothing of that type was emitted.
* TN -- the type was neither expected nor emitted.

Scoring is deliberately per-scenario-and-type, not per-signal: the
product question is "did the tool correctly flag this session for this
kind of problem?", not "how many times did it say so". Counting every
duplicate signal as a separate TP would let a noisy detector inflate its
own recall.

Calibration is measured separately, over individual signals, by bucketing
each emitted signal by its stated confidence and asking what fraction of
that bucket was actually expected. A calibrated 0.8 bucket should be
right about 80% of the time. This is the check that shows whether a
confidence number means anything at all.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from app.analysis.context import (
    MessageView,
    SessionContext,
    ToolCallView,
    ToolResultView,
)
from app.analysis.detectors import default_detectors
from app.analysis.signals import Signal
from app.models import DetectionType, MessageRole

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

# Informational-only signals. `app.analysis.health` deliberately excludes
# these from every health dimension, so treating them as detection
# failures here would contradict the scoring model. Their quality is
# still measured and reported separately -- being informational is not a
# licence to stop checking them.
INFORMATIONAL_TYPES = frozenset(
    {
        DetectionType.CONTEXT_GROWTH,
        DetectionType.BEHAVIOR_SHIFT,
        DetectionType.TOPIC_DRIFT,
    }
)


class CorpusError(ValueError):
    """Raised when a scenario file is malformed or mislabeled."""


@dataclass(frozen=True)
class CorpusScenario:
    """One labeled session.

    `expected` is the set of detection types a correct implementation
    should raise. Every other non-informational type is, by definition, a
    false positive if raised -- which is why `expected` must be written
    from the scenario's intent, never adjusted to match what the
    detectors happen to output.
    """

    id: str
    title: str
    category: str
    description: str
    expected: frozenset[DetectionType]
    context: SessionContext
    source: Path
    notes: str = ""
    # Types that are genuinely arguable for this scenario. They are
    # excluded from FP counting but never count as TP, so an honestly
    # ambiguous signal neither rewards nor punishes the detector.
    tolerated: frozenset[DetectionType] = frozenset()


def _parse_detection_types(
    values: Iterable[str] | None, *, where: str
) -> frozenset[DetectionType]:
    result = set()
    for value in values or []:
        try:
            result.add(DetectionType(value))
        except ValueError as exc:
            raise CorpusError(
                f"{where}: '{value}' is not a known detection type"
            ) from exc
    return frozenset(result)


def _build_context(scenario_id: str, raw_messages: Sequence[dict[str, Any]]):
    base = datetime(2026, 1, 1, tzinfo=UTC)
    messages: list[MessageView] = []
    for index, raw in enumerate(raw_messages, start=1):
        try:
            role = MessageRole(raw["role"])
        except (KeyError, ValueError) as exc:
            raise CorpusError(
                f"{scenario_id}: message {index} has a missing/invalid role"
            ) from exc
        content = raw.get("content")
        if not isinstance(content, str):
            raise CorpusError(
                f"{scenario_id}: message {index} must have string content"
            )

        message_id = f"{scenario_id}-m{index}"
        tool_calls: list[ToolCallView] = []
        for call_index, raw_call in enumerate(raw.get("tool_calls") or []):
            call_id = f"{message_id}-tc{call_index}"
            raw_result = raw_call.get("result")
            result = None
            if raw_result is not None:
                output = raw_result.get("output", {})
                if not isinstance(output, dict):
                    raise CorpusError(
                        f"{scenario_id}: tool result output must be a mapping"
                    )
                result = ToolResultView(
                    id=f"{call_id}-r",
                    tool_call_id=call_id,
                    output=output,
                    is_error=bool(raw_result.get("is_error", False)),
                    created_at=base + timedelta(minutes=index),
                )
            tool_calls.append(
                ToolCallView(
                    id=call_id,
                    message_id=message_id,
                    call_index=call_index,
                    tool_name=raw_call.get("tool_name", "tool"),
                    arguments=raw_call.get("arguments", {}) or {},
                    created_at=base + timedelta(minutes=index),
                    result=result,
                )
            )

        messages.append(
            MessageView(
                id=message_id,
                sequence_number=index,
                role=role,
                content=content,
                created_at=base + timedelta(minutes=index),
                tool_calls=tuple(tool_calls),
            )
        )
    return SessionContext(session_id=scenario_id, messages=messages)


def load_scenario(path: Path) -> CorpusScenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CorpusError(f"{path.name}: expected a YAML mapping")

    for required in ("id", "title", "category", "description", "messages"):
        if required not in raw:
            raise CorpusError(f"{path.name}: missing required key '{required}'")
    if "expected_detections" not in raw:
        raise CorpusError(
            f"{path.name}: missing 'expected_detections' -- write [] explicitly "
            "for a scenario where nothing should fire, so an omission is never "
            "mistaken for a clean label"
        )

    expected = _parse_detection_types(
        raw["expected_detections"], where=f"{path.name} expected_detections"
    )
    tolerated = _parse_detection_types(
        raw.get("tolerated_detections"), where=f"{path.name} tolerated_detections"
    )
    overlap = expected & tolerated
    if overlap:
        raise CorpusError(
            f"{path.name}: {sorted(t.value for t in overlap)} cannot be both "
            "expected and tolerated"
        )

    return CorpusScenario(
        id=str(raw["id"]),
        title=str(raw["title"]),
        category=str(raw["category"]),
        description=str(raw["description"]),
        notes=str(raw.get("notes", "")),
        expected=expected,
        tolerated=tolerated,
        context=_build_context(str(raw["id"]), raw["messages"]),
        source=path,
    )


def load_corpus(directory: Path | None = None) -> list[CorpusScenario]:
    directory = directory or CORPUS_DIR
    scenarios = [load_scenario(p) for p in sorted(directory.glob("*.yaml"))]
    duplicates = {s.id for s in scenarios if [x.id for x in scenarios].count(s.id) > 1}
    if duplicates:
        raise CorpusError(f"duplicate scenario ids: {sorted(duplicates)}")
    return scenarios


@dataclass
class DetectorMetrics:
    detection_type: DetectionType
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    @property
    def support(self) -> int:
        """Scenarios where this type was expected."""
        return self.true_positives + self.false_negatives

    @property
    def precision(self) -> float | None:
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return None
        return self.true_positives / denominator

    @property
    def recall(self) -> float | None:
        if self.support == 0:
            return None
        return self.true_positives / self.support

    @property
    def false_positive_rate(self) -> float | None:
        denominator = self.false_positives + self.true_negatives
        if denominator == 0:
            return None
        return self.false_positives / denominator

    @property
    def f1(self) -> float | None:
        precision, recall = self.precision, self.recall
        if precision is None or recall is None or precision + recall == 0:
            return None
        return 2 * precision * recall / (precision + recall)


@dataclass
class CalibrationBucket:
    lower: float
    upper: float
    signals: int = 0
    correct: int = 0

    @property
    def observed_accuracy(self) -> float | None:
        if self.signals == 0:
            return None
        return self.correct / self.signals

    @property
    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2


@dataclass
class ScenarioResult:
    scenario: CorpusScenario
    emitted: frozenset[DetectionType]
    signals: list[Signal]

    @property
    def missed(self) -> frozenset[DetectionType]:
        return self.scenario.expected - self.emitted

    @property
    def spurious(self) -> frozenset[DetectionType]:
        return (
            self.emitted
            - self.scenario.expected
            - self.scenario.tolerated
            - INFORMATIONAL_TYPES
        )

    @property
    def exact_match(self) -> bool:
        return not self.missed and not self.spurious


@dataclass
class EvaluationReport:
    results: list[ScenarioResult] = field(default_factory=list)
    metrics: dict[DetectionType, DetectorMetrics] = field(default_factory=dict)
    # Measured but excluded from health scoring, so excluded from the
    # headline numbers. Reported separately rather than dropped.
    informational_metrics: dict[DetectionType, DetectorMetrics] = field(
        default_factory=dict
    )
    calibration: list[CalibrationBucket] = field(default_factory=list)

    @property
    def scenario_count(self) -> int:
        return len(self.results)

    @property
    def exact_match_count(self) -> int:
        return sum(1 for r in self.results if r.exact_match)

    @property
    def totals(self) -> DetectorMetrics:
        combined = DetectorMetrics(detection_type=DetectionType.CONTRADICTION)
        for metric in self.metrics.values():
            combined.true_positives += metric.true_positives
            combined.false_positives += metric.false_positives
            combined.false_negatives += metric.false_negatives
            combined.true_negatives += metric.true_negatives
        return combined

    def by_category(self) -> dict[str, tuple[int, int]]:
        """Exact-match count and total, per corpus category."""
        summary: dict[str, list[int]] = {}
        for result in self.results:
            entry = summary.setdefault(result.scenario.category, [0, 0])
            entry[1] += 1
            if result.exact_match:
                entry[0] += 1
        return {k: (v[0], v[1]) for k, v in summary.items()}


def _calibration_buckets() -> list[CalibrationBucket]:
    edges = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    return [
        CalibrationBucket(lower=lo, upper=hi)
        for lo, hi in zip(edges, edges[1:], strict=False)
    ]


def evaluate_corpus(
    scenarios: Sequence[CorpusScenario] | None = None,
) -> EvaluationReport:
    """Run the deterministic detectors over every scenario and score them."""
    scenarios = scenarios if scenarios is not None else load_corpus()
    detectors = default_detectors()
    scored_types = [t for t in DetectionType if t not in INFORMATIONAL_TYPES]

    report = EvaluationReport(
        metrics={t: DetectorMetrics(detection_type=t) for t in scored_types},
        informational_metrics={
            t: DetectorMetrics(detection_type=t)
            for t in sorted(INFORMATIONAL_TYPES, key=lambda t: t.value)
        },
        calibration=_calibration_buckets(),
    )

    for scenario in scenarios:
        signals: list[Signal] = []
        for detector in detectors:
            signals.extend(detector.detect(scenario.context))
        emitted = frozenset(s.detection_type for s in signals)
        report.results.append(
            ScenarioResult(scenario=scenario, emitted=emitted, signals=signals)
        )

        for detection_type in list(scored_types) + sorted(
            INFORMATIONAL_TYPES, key=lambda t: t.value
        ):
            metric = (
                report.metrics.get(detection_type)
                or report.informational_metrics[detection_type]
            )
            is_expected = detection_type in scenario.expected
            was_emitted = detection_type in emitted
            if is_expected and was_emitted:
                metric.true_positives += 1
            elif is_expected and not was_emitted:
                metric.false_negatives += 1
            elif was_emitted and detection_type not in scenario.tolerated:
                metric.false_positives += 1
            elif not was_emitted:
                metric.true_negatives += 1

        for signal in signals:
            if signal.detection_type in INFORMATIONAL_TYPES:
                continue
            bucket = next(
                (
                    b
                    for b in report.calibration
                    if b.lower <= signal.confidence < b.upper
                    or (b.upper == 1.0 and signal.confidence == 1.0)
                ),
                None,
            )
            if bucket is None:
                continue
            bucket.signals += 1
            if signal.detection_type in scenario.expected:
                bucket.correct += 1

    return report


def report_to_dict(report: EvaluationReport) -> dict[str, Any]:
    """Serializable summary, for diffing runs or storing a baseline."""
    return {
        "scenarios": report.scenario_count,
        "exact_matches": report.exact_match_count,
        "by_category": {
            k: {"exact": v[0], "total": v[1]} for k, v in report.by_category().items()
        },
        "metrics": {
            t.value: {
                "support": m.support,
                "tp": m.true_positives,
                "fp": m.false_positives,
                "fn": m.false_negatives,
                "tn": m.true_negatives,
                "precision": m.precision,
                "recall": m.recall,
                "false_positive_rate": m.false_positive_rate,
                "f1": m.f1,
            }
            for t, m in sorted(report.metrics.items(), key=lambda kv: kv[0].value)
        },
        "informational_metrics": {
            t.value: {
                "support": m.support,
                "tp": m.true_positives,
                "fp": m.false_positives,
                "fn": m.false_negatives,
                "precision": m.precision,
                "recall": m.recall,
                "false_positive_rate": m.false_positive_rate,
            }
            for t, m in sorted(
                report.informational_metrics.items(), key=lambda kv: kv[0].value
            )
        },
        "calibration": [
            {
                "range": f"[{b.lower:.1f}, {b.upper:.1f})",
                "signals": b.signals,
                "expected_fraction": b.observed_accuracy,
            }
            for b in report.calibration
        ],
        "per_scenario": [
            {
                "id": r.scenario.id,
                "category": r.scenario.category,
                "expected": sorted(t.value for t in r.scenario.expected),
                "emitted": sorted(t.value for t in r.emitted),
                "missed": sorted(t.value for t in r.missed),
                "spurious": sorted(t.value for t in r.spurious),
                "exact_match": r.exact_match,
            }
            for r in report.results
        ],
    }


def report_to_json(report: EvaluationReport) -> str:
    return json.dumps(report_to_dict(report), indent=2, sort_keys=False)
