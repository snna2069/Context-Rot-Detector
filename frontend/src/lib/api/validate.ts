/**
 * Minimal runtime validation for backend responses.
 *
 * Deliberately hand-written rather than pulling in a schema library: the
 * goal is not to re-specify every field, but to fail fast and clearly at
 * the API boundary on the handful of shapes the UI actually branches on
 * (arrays, score nullability, run status). Previously every response was
 * cast with `as T`, so a backend change surfaced as an inscrutable
 * `undefined is not an object` inside a component.
 *
 * Validators are intentionally permissive about unknown extra fields --
 * the backend adding a field must never break the dashboard.
 */

import type {
  AnalysisRun,
  AnalysisRunStatus,
  AnalysisStatus,
  ContextHealthScore,
} from "@/lib/api/types";

function fail(what: string, value: unknown): never {
  const actual = value === null ? "null" : typeof value;
  throw new Error(`expected ${what}, received ${actual}`);
}

export function expectObject(value: unknown, what: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    fail(what, value);
  }
  return value as Record<string, unknown>;
}

export function expectArray(value: unknown, what: string): unknown[] {
  if (!Array.isArray(value)) fail(what, value);
  return value;
}

function expectNumberOrNull(value: unknown, what: string): number | null {
  if (value === null) return null;
  if (typeof value !== "number" || Number.isNaN(value)) fail(what, value);
  return value;
}

const RUN_STATUSES: readonly AnalysisRunStatus[] = [
  "pending",
  "running",
  "completed",
  "partial",
  "failed",
];

function expectRunStatus(value: unknown): AnalysisRunStatus {
  if (typeof value !== "string" || !RUN_STATUSES.includes(value as AnalysisRunStatus)) {
    throw new Error(
      `expected a known analysis run status, received ${JSON.stringify(value)}`,
    );
  }
  return value as AnalysisRunStatus;
}

/** Validates the fields the UI branches on, then trusts the rest. */
export function parseAnalysisRun(value: unknown): AnalysisRun {
  const run = expectObject(value, "an analysis run object");
  expectRunStatus(run.status);
  expectArray(run.failed_detectors ?? [], "failed_detectors to be an array");
  return {
    ...(run as unknown as AnalysisRun),
    // Older backends omit the field entirely; treat that as "no known
    // failures" rather than letting `.map` crash in the UI.
    failed_detectors: (run.failed_detectors ?? []) as AnalysisRun["failed_detectors"],
  };
}

export function parseAnalysisStatus(value: unknown): AnalysisStatus {
  const status = expectObject(value, "an analysis status object");
  if (typeof status.is_stale !== "boolean") {
    fail("is_stale to be a boolean", status.is_stale);
  }
  if (typeof status.messages_since_analysis !== "number") {
    fail("messages_since_analysis to be a number", status.messages_since_analysis);
  }
  return {
    ...(status as unknown as AnalysisStatus),
    latest_run:
      status.latest_run === null || status.latest_run === undefined
        ? null
        : parseAnalysisRun(status.latest_run),
  };
}

/**
 * A health score's dimension fields are nullable by design -- `null`
 * means "not assessed", which the UI must render differently from a real
 * score. Validating them here keeps a malformed payload from silently
 * becoming `undefined` and rendering as a blank/zero bar.
 */
export function parseHealthScore(value: unknown): ContextHealthScore {
  const score = expectObject(value, "a health score object");
  if (typeof score.overall_score !== "number") {
    fail("overall_score to be a number", score.overall_score);
  }
  for (const key of [
    "relevance_score",
    "consistency_score",
    "instruction_adherence_score",
    "information_retention_score",
    "tool_utilization_score",
    "hallucination_risk_score",
  ] as const) {
    expectNumberOrNull(score[key], `${key} to be a number or null`);
  }
  return score as unknown as ContextHealthScore;
}

/** Builds a validator for a JSON array of `item`s. */
export function arrayOf<T>(
  item: (value: unknown) => T,
  what: string,
): (value: unknown) => T[] {
  return (value: unknown) => expectArray(value, what).map(item);
}
