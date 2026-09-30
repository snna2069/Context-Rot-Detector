import type { AnalysisStatus } from "@/lib/api/types";
import { ExclamationTriangleIcon } from "@/components/icons";

/**
 * Warns when stored analysis results should not be read at face value.
 *
 * Two distinct cases, both of which otherwise render as a reassuringly
 * clean dashboard:
 *
 * 1. The run did not fully complete (`partial`/`failed`). "No
 *    detections" then may mean "the detector never ran", not "the
 *    detector looked and found nothing".
 * 2. The run is stale -- messages were ingested after it. The stored
 *    detections and score describe only part of the session and say
 *    nothing at all about the newer messages.
 *
 * For a monitoring tool, silently presenting either as a healthy result
 * is the most dangerous possible failure mode.
 */
export function AnalysisIntegrityNotice({
  status,
}: {
  status: AnalysisStatus | null;
}) {
  if (status === null || !status.has_been_analyzed) return null;

  const run = status.latest_run;
  const incomplete = run?.status === "partial" || run?.status === "failed";
  const isTotalFailure = run?.status === "failed";

  if (!incomplete && !status.is_stale) return null;

  const tone = isTotalFailure
    ? {
        border: "border-red-300 bg-red-50",
        head: "text-red-800",
        body: "text-red-700",
      }
    : {
        border: "border-amber-300 bg-amber-50",
        head: "text-amber-800",
        body: "text-amber-700",
      };

  return (
    <div role="alert" className={`rounded-xl border p-4 ${tone.border}`}>
      <h2
        className={`inline-flex items-center gap-2 text-sm font-semibold ${tone.head}`}
      >
        <ExclamationTriangleIcon className="h-4 w-4" aria-hidden="true" />
        {isTotalFailure
          ? "Analysis failed — these results are not usable"
          : incomplete
            ? "Analysis incomplete — results are partial"
            : "Results are out of date"}
      </h2>

      {incomplete ? (
        <p className={`mt-1.5 text-sm ${tone.body}`}>
          {isTotalFailure
            ? "No detector completed, so nothing about this session was actually assessed. A missing detection here does not mean the session is healthy."
            : "Some detectors did not complete, so the dimensions they cover were not assessed. Treat those as unknown, not as clean."}
        </p>
      ) : null}

      {status.is_stale ? (
        <p className={`mt-1.5 text-sm ${tone.body}`}>
          {status.messages_since_analysis}{" "}
          {status.messages_since_analysis === 1 ? "message has" : "messages have"}{" "}
          been ingested since the last analysis run
          {status.analyzed_through_sequence !== null
            ? ` (which covered messages up to #${status.analyzed_through_sequence})`
            : ""}
          . These results say nothing about those newer messages — run analysis
          again to include them.
        </p>
      ) : null}

      {incomplete && run && run.failed_detectors.length > 0 ? (
        <ul className={`mt-3 space-y-1 text-xs ${tone.body}`}>
          {run.failed_detectors.map((detector) => (
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

      {incomplete && run?.error_message ? (
        <p className={`mt-3 text-xs ${tone.body}`}>{run.error_message}</p>
      ) : null}
    </div>
  );
}
