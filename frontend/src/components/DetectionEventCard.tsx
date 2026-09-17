import Link from "next/link";
import type { DetectionEvent } from "@/lib/api/types";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ChevronRightIcon } from "@/components/icons";
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

const severityAccentClasses: Record<DetectionEvent["severity"], string> = {
  info: "bg-slate-300",
  low: "bg-blue-400",
  medium: "bg-amber-400",
  high: "bg-orange-400",
  critical: "bg-red-500",
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
      className="group flex overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
    >
      <span className={`w-1.5 flex-none ${severityAccentClasses[event.severity]}`} />
      <div className="flex-1 p-4">
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
            <ChevronRightIcon className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-indigo-500" />
          </div>
        </div>
        <p className="mt-2 text-sm text-slate-600">{event.explanation}</p>
      </div>
    </Link>
  );
}
