"""Tests for the evaluation harness itself.

The harness is a measurement instrument, so its arithmetic has to be
trustworthy before any number it produces means anything. These tests
pin the metric definitions and the corpus-loading guard rails; they say
nothing about detector quality, which is what `python -m evaluation`
reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.models import DetectionType
from evaluation.harness import (
    INFORMATIONAL_TYPES,
    CorpusError,
    evaluate_corpus,
    load_corpus,
    load_scenario,
    report_to_dict,
)


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _scenario(**overrides) -> dict:
    base = {
        "id": "s1",
        "title": "t",
        "category": "benign_variation",
        "description": "d",
        "expected_detections": [],
        "messages": [{"role": "user", "content": "hello"}],
    }
    base.update(overrides)
    return base


class _FixedDetector:
    """Emits a preset list of types regardless of input."""

    name = "fixed"
    detection_types = frozenset()

    def __init__(self, types):
        self._types = types

    def detect(self, context):
        from app.analysis.signals import Signal
        from app.models import DetectionSeverity

        return [
            Signal(
                detector_name="fixed",
                detection_type=t,
                severity=DetectionSeverity.MEDIUM,
                confidence=0.9,
                explanation="x",
            )
            for t in self._types
        ]


def test_missing_expected_detections_is_rejected(tmp_path: Path) -> None:
    """An unlabeled scenario must never be silently treated as clean."""
    data = _scenario()
    del data["expected_detections"]
    path = _write(tmp_path, "a.yaml", data)

    with pytest.raises(CorpusError, match="expected_detections"):
        load_scenario(path)


def test_unknown_detection_type_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path, "a.yaml", _scenario(expected_detections=["not_a_real_type"])
    )

    with pytest.raises(CorpusError, match="not a known detection type"):
        load_scenario(path)


def test_type_cannot_be_both_expected_and_tolerated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "a.yaml",
        _scenario(
            expected_detections=["contradiction"],
            tolerated_detections=["contradiction"],
        ),
    )

    with pytest.raises(CorpusError, match="cannot be both"):
        load_scenario(path)


def test_duplicate_scenario_ids_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "a.yaml", _scenario(id="dup"))
    _write(tmp_path, "b.yaml", _scenario(id="dup"))

    with pytest.raises(CorpusError, match="duplicate scenario ids"):
        load_corpus(tmp_path)


def test_tool_calls_and_results_are_loaded(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "a.yaml",
        _scenario(
            messages=[
                {
                    "role": "assistant",
                    "content": "checking",
                    "tool_calls": [
                        {
                            "tool_name": "get_status",
                            "arguments": {"env": "prod"},
                            "result": {"output": {"v": 1}, "is_error": True},
                        }
                    ],
                }
            ]
        ),
    )

    scenario = load_scenario(path)

    call = scenario.context.messages[0].tool_calls[0]
    assert call.tool_name == "get_status"
    assert call.result is not None
    assert call.result.is_error is True
    assert call.result.output == {"v": 1}


def test_messages_are_sequenced_in_file_order(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "a.yaml",
        _scenario(
            messages=[
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
                {"role": "user", "content": "third"},
            ]
        ),
    )

    scenario = load_scenario(path)

    assert [m.sequence_number for m in scenario.context.messages] == [1, 2, 3]
    assert [m.content for m in scenario.context.messages] == [
        "first",
        "second",
        "third",
    ]


def test_expected_and_emitted_counts_as_true_positive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import evaluation.harness as harness

    monkeypatch.setattr(
        harness,
        "default_detectors",
        lambda: [_FixedDetector([DetectionType.CONTRADICTION])],
    )
    _write(tmp_path, "a.yaml", _scenario(expected_detections=["contradiction"]))

    report = evaluate_corpus(load_corpus(tmp_path))

    metric = report.metrics[DetectionType.CONTRADICTION]
    assert (metric.true_positives, metric.false_positives) == (1, 0)
    assert metric.precision == 1.0
    assert metric.recall == 1.0
    assert report.exact_match_count == 1


def test_unexpected_emission_counts_as_false_positive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import evaluation.harness as harness

    monkeypatch.setattr(
        harness,
        "default_detectors",
        lambda: [_FixedDetector([DetectionType.CONTRADICTION])],
    )
    _write(tmp_path, "a.yaml", _scenario(expected_detections=[]))

    report = evaluate_corpus(load_corpus(tmp_path))

    metric = report.metrics[DetectionType.CONTRADICTION]
    assert (metric.true_positives, metric.false_positives) == (0, 1)
    assert metric.precision == 0.0
    assert report.exact_match_count == 0


def test_expected_but_absent_counts_as_false_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import evaluation.harness as harness

    monkeypatch.setattr(harness, "default_detectors", lambda: [_FixedDetector([])])
    _write(tmp_path, "a.yaml", _scenario(expected_detections=["contradiction"]))

    report = evaluate_corpus(load_corpus(tmp_path))

    metric = report.metrics[DetectionType.CONTRADICTION]
    assert metric.false_negatives == 1
    assert metric.recall == 0.0


def test_tolerated_type_is_neither_true_nor_false_positive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import evaluation.harness as harness

    monkeypatch.setattr(
        harness,
        "default_detectors",
        lambda: [_FixedDetector([DetectionType.CONTRADICTION])],
    )
    _write(
        tmp_path,
        "a.yaml",
        _scenario(expected_detections=[], tolerated_detections=["contradiction"]),
    )

    report = evaluate_corpus(load_corpus(tmp_path))

    metric = report.metrics[DetectionType.CONTRADICTION]
    assert metric.false_positives == 0
    assert metric.true_positives == 0
    assert report.exact_match_count == 1


def test_informational_types_are_never_false_positives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """They are excluded from health scoring, so they must not be scored."""
    import evaluation.harness as harness

    monkeypatch.setattr(
        harness,
        "default_detectors",
        lambda: [_FixedDetector(list(INFORMATIONAL_TYPES))],
    )
    _write(tmp_path, "a.yaml", _scenario(expected_detections=[]))

    report = evaluate_corpus(load_corpus(tmp_path))

    assert report.exact_match_count == 1
    for informational in INFORMATIONAL_TYPES:
        assert informational not in report.metrics


def test_duplicate_signals_do_not_inflate_recall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scoring is per scenario and type, not per signal."""
    import evaluation.harness as harness

    monkeypatch.setattr(
        harness,
        "default_detectors",
        lambda: [
            _FixedDetector([DetectionType.CONTRADICTION, DetectionType.CONTRADICTION])
        ],
    )
    _write(tmp_path, "a.yaml", _scenario(expected_detections=["contradiction"]))

    report = evaluate_corpus(load_corpus(tmp_path))

    assert report.metrics[DetectionType.CONTRADICTION].true_positives == 1


def test_calibration_buckets_count_signals_against_expectation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import evaluation.harness as harness

    monkeypatch.setattr(
        harness,
        "default_detectors",
        lambda: [_FixedDetector([DetectionType.CONTRADICTION])],
    )
    _write(
        tmp_path, "a.yaml", _scenario(id="hit", expected_detections=["contradiction"])
    )
    _write(tmp_path, "b.yaml", _scenario(id="miss", expected_detections=[]))

    report = evaluate_corpus(load_corpus(tmp_path))

    bucket = next(b for b in report.calibration if b.lower == 0.9)
    assert bucket.signals == 2
    assert bucket.correct == 1
    assert bucket.observed_accuracy == 0.5


def test_report_serialises_to_a_stable_dict() -> None:
    report = evaluate_corpus(load_corpus())

    data = report_to_dict(report)

    assert data["scenarios"] == report.scenario_count
    assert set(data) == {
        "scenarios",
        "exact_matches",
        "by_category",
        "metrics",
        "informational_metrics",
        "calibration",
        "per_scenario",
    }


def test_real_corpus_loads_and_every_scenario_is_labeled() -> None:
    scenarios = load_corpus()

    assert len(scenarios) >= 15
    known_categories = {
        "genuine_degradation",
        "benign_variation",
        "ambiguous",
        "sparse_context",
        "tool_usage",
        "long_session",
    }
    for scenario in scenarios:
        assert scenario.category in known_categories, scenario.id
        assert scenario.description.strip(), scenario.id


def test_corpus_contains_both_positive_and_negative_scenarios() -> None:
    """A corpus of only positives cannot measure false positives."""
    scenarios = load_corpus()

    positives = [s for s in scenarios if s.expected]
    negatives = [s for s in scenarios if not s.expected and not s.tolerated]

    assert len(positives) >= 5
    assert len(negatives) >= 5


def test_evaluation_is_deterministic() -> None:
    """Two runs over the same corpus must agree exactly."""
    first = report_to_dict(evaluate_corpus(load_corpus()))
    second = report_to_dict(evaluate_corpus(load_corpus()))

    assert first == second


def test_detection_quality_has_not_regressed_below_baseline() -> None:
    """Guards the measured baseline recorded in `evaluation/baseline.json`.

    These thresholds are a *regression floor*, not a quality target. They
    are set slightly below the values measured when the baseline was
    recorded, so an unrelated change that quietly degrades detection
    quality fails here instead of going unnoticed.

    They are deliberately NOT a claim that the detectors are accurate:
    the corpus is small, author-written and single-labeled. See
    `evaluation/corpus/README.md`.
    """
    report = evaluate_corpus(load_corpus())
    totals = report.totals

    assert totals.precision is not None
    assert totals.recall is not None
    # Measured at the Phase 3 baseline: precision 0.80, recall 0.50,
    # 16/21 exact matches.
    assert totals.precision >= 0.75, f"precision regressed to {totals.precision:.3f}"
    assert totals.recall >= 0.45, f"recall regressed to {totals.recall:.3f}"
    assert report.exact_match_count >= 15


def test_no_signals_fire_on_an_empty_or_minimal_session() -> None:
    """Sparse sessions cannot exhibit degradation; anything here is noise."""
    sparse = [s for s in load_corpus() if s.category == "sparse_context"]
    assert sparse, "the corpus must retain sparse-context scenarios"

    report = evaluate_corpus(sparse)

    for result in report.results:
        assert not result.spurious, f"{result.scenario.id}: {result.spurious}"
