import {
  detectionEventLimit,
  getAnalysisStatus,
  listDetectionEvents,
} from "@/lib/api/analysis";
import { orNotFound } from "@/lib/api/client";
import { AnalysisIntegrityNotice } from "@/components/AnalysisIntegrityNotice";
import { EmptyState } from "@/components/EmptyState";
import { DetectionEventsFilterList } from "@/components/DetectionEventsFilterList";

export default async function SessionEventsPage({
  params,
}: PageProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const [events, status] = await Promise.all([
    orNotFound(listDetectionEvents(sessionId)),
    orNotFound(getAnalysisStatus(sessionId)),
  ]);

  return (
    <div className="space-y-6">
      <AnalysisIntegrityNotice status={status} />
      {events.length >= detectionEventLimit ? (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
          Showing the {detectionEventLimit} most recent detection events. Older
          events for this session are not listed here.
        </p>
      ) : null}
      {events.length === 0 ? (
        <EmptyState
          title="No detection events yet"
          description={'Run analysis on this session ("Run analysis" above) to check for signals.'}
        />
      ) : (
        <DetectionEventsFilterList sessionId={sessionId} events={events} />
      )}
    </div>
  );
}
