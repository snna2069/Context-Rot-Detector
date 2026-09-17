import Link from "next/link";
import { listDetectionEvents } from "@/lib/api/analysis";
import { orNotFound } from "@/lib/api/client";
import { EmptyState } from "@/components/EmptyState";
import { SeverityBadge } from "@/components/SeverityBadge";
import { NotVerifiedTag } from "@/components/NotVerifiedTag";
import {
  compareClassificationSeverity,
  formatScorePercent,
  formatTimestamp,
  hallucinationClassificationLabels,
  isHallucinationClassification,
} from "@/lib/format";
import type { DetectionEvent, HallucinationClassification } from "@/lib/api/types";

export default async function SessionHallucinationsPage({
  params,
}: PageProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const events = await orNotFound(listDetectionEvents(sessionId));

  const claimEvents = events.filter(
    (event) => event.detection_type === "unsupported_claim",
  );

  const groups = new Map<HallucinationClassification, DetectionEvent[]>();
  for (const event of claimEvents) {
    const classification = event.metadata["classification"];
    if (!isHallucinationClassification(classification)) continue;
    const bucket = groups.get(classification) ?? [];
    bucket.push(event);
    groups.set(classification, bucket);
  }

  const orderedClassifications = Array.from(groups.keys()).sort(
    compareClassificationSeverity,
  );

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-medium">
          These are automated, evidence-based classifications -- not
          confirmed facts.
        </p>
        <p className="mt-1 text-amber-800">
          This system has no external fact-checking oracle. Every item below
          is derived from comparing an agent claim against evidence
          available within this session (or the absence of it). Even a
          &quot;high-confidence hallucination&quot; label is a probabilistic
          estimate, not an independently verified determination -- there is
          currently no mechanism in this system that produces a
          &quot;verified hallucination&quot; status.
        </p>
      </div>

      {claimEvents.length === 0 ? (
        <EmptyState
          title="No claims flagged"
          description="Either no unsupported-claim signals have been detected, or analysis has not been run yet for this session."
        />
      ) : (
        <div className="space-y-6">
          {orderedClassifications.map((classification) => {
            const items = groups.get(classification)!;
            return (
              <section key={classification}>
                <div className="mb-2 flex items-center gap-2">
                  <h2 className="font-medium text-slate-900">
                    {hallucinationClassificationLabels[classification]}
                  </h2>
                  <span className="text-xs text-slate-400">
                    {items.length} item{items.length === 1 ? "" : "s"}
                  </span>
                  <NotVerifiedTag />
                </div>
                <div className="space-y-3">
                  {items.map((event) => (
                    <Link
                      key={event.id}
                      href={`/sessions/${sessionId}/events/${event.id}`}
                      className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <SeverityBadge severity={event.severity} />
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span>
                            Confidence {formatScorePercent(event.confidence)}
                          </span>
                          <span>{formatTimestamp(event.timestamp)}</span>
                        </div>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">
                        {event.explanation}
                      </p>
                    </Link>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
