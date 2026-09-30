import type { AnalysisRun } from "@/lib/api/types";
import { ExclamationTriangleIcon } from "@/components/icons";

/**
 * Warns that an analysis run did not fully complete.
 *
 * This exists because "no detections" is ambiguous: it can mean the
 * detectors looked and found nothing, or that they never ran. Without
 * this notice a transient LLM outage would render as a clean, healthy
 * session -- the most dangerous possible failure mode for a monitoring
 * tool. Absence of a signal from a failed detector is not evidence that
 * the condition is absent.
 */
export function AnalysisIntegrityNotice({ run }: { run: AnalysisRun | null }) {
  if (run === null) return null;
  if (run.status !== "partial" && run.status !== "failed") return null;

  const failed = run.failed_detectors ?? [];
  const isTotalFailure = run.status === "failed";

  return (
    <div
      role="alert"
      className={`rounded-xl border p-4 ${
        isTotalFailure
          ? "border-red-300 bg-red-50"
          : "border-amber-300 bg-amber-50"
      }`}
    >
      <h2
        className={`inline-flex items-center gap-2 text-sm font-semibold ${
          isTotalFailure ? "text-red-800" : "text-amber-800"
        }`}
      >
        <ExclamationTriangleIcon className="h-4 w-4" aria-hidden="true" />
        {isTotalFailure
          ? "Analysis failed — these results are not usable"
          : "Analysis incomplete — results are partial"}
      </h2>
      <p
        className={`mt-1.5 text-sm ${
          isTotalFailure ? "text-red-700" : "text-amber-700"
        }`}
      >
        {isTotalFailure
          ? "No detector completed, so nothing about this session was actually assessed. A missing detection here does not mean the session is healthy."
          : "Some detectors did not complete, so the dimensions they cover were not assessed. Treat those as unknown, not as clean."}
      </p>
      {failed.length > 0 ? (
        <ul
          className={`mt-3 space-y-1 text-xs ${
            isTotalFailure ? "text-red-700" : "text-amber-700"
          }`}
        >
          {failed.map((detector) => (
            <li key={detector.detector} className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 flex-none rounded-full bg-current" />
              <span>
                <span className="font-medium">{detector.detector}</span>
                {detector.error ? ` — ${detector.error}` : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      {run.error_message ? (
        <p
          className={`mt-3 text-xs ${
            isTotalFailure ? "text-red-600" : "text-amber-600"
          }`}
        >
          {run.error_message}
        </p>
      ) : null}
    </div>
  );
}
