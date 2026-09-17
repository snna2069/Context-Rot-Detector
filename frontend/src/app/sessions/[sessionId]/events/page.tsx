import { listDetectionEvents } from "@/lib/api/analysis";
import { orNotFound } from "@/lib/api/client";
import { EmptyState } from "@/components/EmptyState";
import { DetectionEventsFilterList } from "@/components/DetectionEventsFilterList";

export default async function SessionEventsPage({
  params,
}: PageProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const events = await orNotFound(listDetectionEvents(sessionId));

  if (events.length === 0) {
    return (
      <EmptyState
        title="No detection events yet"
        description={'Run analysis on this session ("Run analysis" above) to check for signals.'}
      />
    );
  }

  return <DetectionEventsFilterList sessionId={sessionId} events={events} />;
}
