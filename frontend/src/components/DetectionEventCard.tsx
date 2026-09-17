import Link from "next/link";
import type { DetectionEvent } from "@/lib/api/types";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatScorePercent, formatTimestamp } from "@/lib/format";

const detectionTypeLabels: Record<DetectionEvent["detection_type"], string> = {
  contradiction: "Contradiction",
  instruction_drift: "Instruction drift",
  stale_context: "Stale context",
  repetition: "Repetition",
  unsupported_claim: "Unsupported claim",
  tool_result_misuse: "Tool-result neglect",
  context_growth: "Context growth",
  omission: "Information omission",
  topic_drift: "Topic/relevance drift",
  behavior_shift: "Behavior shift",
  fact_loss: "Loss of established fact",
};

export function detectionTypeLabel(type: DetectionEvent["detection_type"]): string {
  return detectionTypeLabels[type] ?? type;
}

export function DetectionEventCard({
  sessionId,
  event,
}: {
  sessionId: string;
  event: DetectionEvent;
}) {
  return (
    <Link
      href={`/sessions/${sessionId}/events/${event.id}`}
      className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={event.severity} />
          <span className="text-sm font-medium text-slate-900">
            {detectionTypeLabel(event.detection_type)}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>Confidence {formatScorePercent(event.confidence)}</span>
          <span>{formatTimestamp(event.timestamp)}</span>
        </div>
      </div>
      <p className="mt-2 text-sm text-slate-600">{event.explanation}</p>
    </Link>
  );
}
