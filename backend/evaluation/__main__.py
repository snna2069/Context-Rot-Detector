"""CLI entry point: `python -m evaluation`.

Prints a detection-quality report for the labeled corpus. Deterministic
detectors only -- no LLM calls, no cost, no network.
"""

from __future__ import annotations

import argparse
import sys

from evaluation.harness import (
    EvaluationReport,
    evaluate_corpus,
    load_corpus,
    report_to_json,
)


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:5.1f}%"


def _print_report(report: EvaluationReport) -> None:
    print("=" * 78)
    print("DETECTION-QUALITY EVALUATION")
    print("=" * 78)
    print(
        f"\nScenarios: {report.scenario_count}    "
        f"Exact matches: {report.exact_match_count}"
        f"/{report.scenario_count}"
    )

    print("\nBy category (exact match = no missed and no spurious detections):")
    for category, (exact, total) in sorted(report.by_category().items()):
        print(f"  {category:<22} {exact:>3}/{total:<3}")

    print("\nPer detection type:")
    header = (
        f"  {'type':<22}{'supp':>5}{'TP':>4}{'FP':>4}{'FN':>4}"
        f"{'precision':>11}{'recall':>9}{'FPR':>9}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for detection_type in sorted(report.metrics, key=lambda t: t.value):
        m = report.metrics[detection_type]
        if m.support == 0 and m.false_positives == 0:
            continue
        print(
            f"  {detection_type.value:<22}{m.support:>5}{m.true_positives:>4}"
            f"{m.false_positives:>4}{m.false_negatives:>4}"
            f"{_pct(m.precision):>11}{_pct(m.recall):>9}"
            f"{_pct(m.false_positive_rate):>9}"
        )

    totals = report.totals
    print(
        f"\n  {'OVERALL':<22}{totals.support:>5}{totals.true_positives:>4}"
        f"{totals.false_positives:>4}{totals.false_negatives:>4}"
        f"{_pct(totals.precision):>11}{_pct(totals.recall):>9}"
        f"{_pct(totals.false_positive_rate):>9}"
    )

    informational = {
        t: m
        for t, m in report.informational_metrics.items()
        if m.support or m.false_positives
    }
    if informational:
        print(
            "\nInformational signals (surfaced to users but excluded from the"
            "\nhealth score, so excluded from the totals above):"
        )
        print(header)
        print("  " + "-" * (len(header) - 2))
        for detection_type in sorted(informational, key=lambda t: t.value):
            m = informational[detection_type]
            print(
                f"  {detection_type.value:<22}{m.support:>5}{m.true_positives:>4}"
                f"{m.false_positives:>4}{m.false_negatives:>4}"
                f"{_pct(m.precision):>11}{_pct(m.recall):>9}"
                f"{_pct(m.false_positive_rate):>9}"
            )

    print("\nConfidence calibration (are the numbers meaningful?):")
    print(f"  {'confidence':<14}{'signals':>9}{'expected':>10}  interpretation")
    print("  " + "-" * 58)
    any_signals = False
    for bucket in report.calibration:
        if bucket.signals == 0:
            continue
        any_signals = True
        observed = bucket.observed_accuracy
        gap = None if observed is None else observed - bucket.midpoint
        note = ""
        if gap is not None:
            if gap < -0.25:
                note = "overconfident"
            elif gap > 0.25:
                note = "underconfident"
            else:
                note = "roughly aligned"
        print(
            f"  [{bucket.lower:.1f}, {bucket.upper:.1f})  {bucket.signals:>9}"
            f"{_pct(observed):>10}  {note}"
        )
    if not any_signals:
        print("  (no signals emitted)")

    imperfect = [r for r in report.results if not r.exact_match]
    if imperfect:
        print(f"\nScenarios with mismatches ({len(imperfect)}):")
        for result in imperfect:
            print(f"\n  {result.scenario.id}  [{result.scenario.category}]")
            if result.missed:
                print(
                    "    missed:   " + ", ".join(sorted(t.value for t in result.missed))
                )
            if result.spurious:
                print(
                    "    spurious: "
                    + ", ".join(sorted(t.value for t in result.spurious))
                )

    print(
        "\nNOTE: this corpus is small, author-written and single-labeled. "
        "\nTreat these as a regression baseline, not a measure of real-world "
        "accuracy.\nSee evaluation/corpus/README.md for the full limitations."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation",
        description="Measure detector quality against the labeled corpus.",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    parser.add_argument(
        "--fail-under-precision",
        type=float,
        default=None,
        metavar="P",
        help=(
            "exit non-zero if overall precision falls below P (0-1). "
            "Only set this once a baseline has been established."
        ),
    )
    args = parser.parse_args(argv)

    report = evaluate_corpus(load_corpus())

    if args.json:
        print(report_to_json(report))
    else:
        _print_report(report)

    if args.fail_under_precision is not None:
        precision = report.totals.precision
        if precision is not None and precision < args.fail_under_precision:
            print(
                f"\nFAIL: overall precision {precision:.3f} is below the "
                f"configured threshold {args.fail_under_precision:.3f}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
