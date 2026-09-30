import { listAnalysisRuns, listDetectionEvents } from "@/lib/api/analysis";
import { orNotFound } from "@/lib/api/client";
import { AnalysisIntegrityNotice } from "@/components/AnalysisIntegrityNotice";
import { EmptyState } from "@/components/EmptyState";
import { DetectionEventsFilterList } from "@/components/DetectionEventsFilterList";

export default async function SessionEventsPage({
  params,
}: PageProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const [events, runs] = await Promise.all([
    orNotFound(listDetectionEvents(sessionId)),
    orNotFound(listAnalysisRuns(sessionId)),
  ]);

  const latestRun = runs.length > 0 ? runs[0] : null;

  return (
    <div className="space-y-6">
      <AnalysisIntegrityNotice run={latestRun} />
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
