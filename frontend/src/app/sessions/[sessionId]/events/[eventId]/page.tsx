import { notFound } from "next/navigation";
import Link from "next/link";
import { listDetectionEvents } from "@/lib/api/analysis";
import { getSessionTimeline } from "@/lib/api/sessions";
import { orNotFound } from "@/lib/api/client";
import { SeverityBadge } from "@/components/SeverityBadge";
import { NotVerifiedTag } from "@/components/NotVerifiedTag";
import { detectionTypeLabel } from "@/components/DetectionEventCard";
import {
  formatScorePercent,
  formatTimestamp,
  hallucinationClassificationLabels,
  isHallucinationClassification,
} from "@/lib/format";
import type { MessageTimelineEntry } from "@/lib/api/types";

/** There is no dedicated single-event backend endpoint yet -- this fetches
 * the full events list (already small and cached per-request by the
 * backend) and picks the one we need. See ARCHITECTURE.md Phase 7 notes
 * for the tradeoff. */
export default async function DetectionEventDetailPage({
  params,
}: PageProps<"/sessions/[sessionId]/events/[eventId]">) {
  const { sessionId, eventId } = await params;
  const [events, timeline] = await Promise.all([
    orNotFound(listDetectionEvents(sessionId)),
    orNotFound(getSessionTimeline(sessionId)),
  ]);

  const event = events.find((e) => e.id === eventId);
  if (!event) {
    notFound();
  }

  const messagesById = new Map<string, MessageTimelineEntry>(
    timeline.messages.map((m) => [m.id, m]),
  );

  const classification = event.metadata["classification"];
  const externalVerification = event.metadata["external_verification_available"];

  return (
    <div className="space-y-6">
      <Link
        href={`/sessions/${sessionId}/events`}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Back to detection events
      </Link>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={event.severity} />
          <h1 className="text-xl font-semibold text-slate-900">
            {detectionTypeLabel(event.detection_type)}
          </h1>
          {isHallucinationClassification(classification) ? (
            <>
              <span className="rounded-full border border-slate-300 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                {hallucinationClassificationLabels[classification]}
              </span>
              <NotVerifiedTag />
            </>
          ) : null}
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Detected {formatTimestamp(event.timestamp)} · Confidence{" "}
          {formatScorePercent(event.confidence)}
        </p>
        <p className="mt-4 text-sm leading-relaxed text-slate-800">
          {event.explanation}
        </p>
        {typeof externalVerification === "boolean" && !externalVerification ? (
          <p className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
            No external verification was available for this claim -- this
            detection is based solely on comparing statements within this
            session.
          </p>
        ) : null}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-medium text-slate-900">Evidence</h2>
        {event.evidence.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            No structured evidence records were attached to this event.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {event.evidence.map((evidence) => (
              <li
                key={evidence.id}
                className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm"
              >
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {evidence.evidence_role}
                </div>
                {evidence.excerpt ? (
                  <p className="mt-1 whitespace-pre-wrap text-slate-700">
                    {evidence.excerpt}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-medium text-slate-900">Source messages</h2>
        {event.related_message_ids.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            No specific source messages were linked to this event.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {event.related_message_ids.map((messageId) => {
              const message = messagesById.get(messageId);
              return (
                <li
                  key={messageId}
                  className="rounded-md border border-slate-200 p-3 text-sm"
                >
                  <div className="text-xs text-slate-400">
                    {message
                      ? `#${message.sequence_number} · ${message.role}`
                      : messageId}
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-slate-700">
                    {message?.content ?? "(message no longer available)"}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {Object.keys(event.metadata).length > 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-medium text-slate-900">Detector metadata</h2>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            {Object.entries(event.metadata).map(([key, value]) => (
              <div key={key} className="contents">
                <dt className="text-slate-500">{key}</dt>
                <dd className="text-slate-800">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </div>
  );
}
